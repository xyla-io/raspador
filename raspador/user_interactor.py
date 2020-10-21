import click
import logging
import signal
import time
import code
import os
import re
import subprocess
import pdb
import glob
import IPython
import bpython
import collections
import pandas as pd

from config import user_config
from typing import Optional, List, Dict, Callable, Union
from pprint import pformat
from .base import MenuOption, ControlMode, ControlAction
from .error import RaspadorInputTimeoutError, RaspadorCannotInteractError, RaspadorQuit
from .style import Styled, CustomStyled, CodeStyled, Format
from datetime import datetime
from enum import Enum

class Interaction(MenuOption):
  html = 'h'
  image = 'i'
  python = 'p'
  script = 'r'
  debugger = 'd'
  log = 'l'

  @property
  def option_text(self) -> str:
    if self is Interaction.html:
      return '(H)TML current page view'
    elif self is Interaction.image:
      return '(I)mage of current page'
    elif self is Interaction.python:
      return '(P)ython interactive shell'
    elif self is Interaction.script:
      return '(R)un python script'
    elif self is Interaction.debugger:
      return '(D)ebugger session'
    elif self is Interaction.log:
      return '(L)og view'

  @property
  def styled(self) -> Styled:
    return CustomStyled(text=self.option_text, style=Format().blue())

class Console(code.InteractiveConsole):
  record: List = None

  def raw_input(self, prompt=''):
    result = super().raw_input(prompt=prompt)
    if self.record is None:
      self.record = []
    self.record.append(result)
    return result

class UserExceptionFormatter(logging.Formatter):
  style: Format = Format().red().bold()
  def formatException(self, exc_info):
    return self.style(super(UserExceptionFormatter, self).formatException(exc_info))

  def format(self, record):
    s = super(UserExceptionFormatter, self).format(record)
    if record.exc_text:
      s = self.style(s)
    return s

class UserInteractor:
  driver: Optional[any]
  locals: Dict[str, any]
  timeout: Optional[int]
  interactive: bool
  monitor: bool
  control_mode: ControlMode
  break_on_exceptions: bool
  retry: Optional[int]
  abbreviated_length: int
  _last_script_name: Optional[str]=None

  def __init__(self, driver: Optional[any]=None, locals: Dict[str, any]={}, timeout: Optional[int]=30, interactive: bool=True, monitor: bool=False, control_mode: ControlMode=ControlMode.automatic, break_on_exceptions: bool=False, retry: Optional[int]=None, abbreviated_length: int=2048):
    self.driver = driver
    self.timeout = timeout
    self.locals = self.python_locals
    self.locals.update(locals)
    self.interactive = interactive
    self.control_mode = control_mode
    self.break_on_exceptions = break_on_exceptions
    self.retry = retry
    self.abbreviated_length = abbreviated_length

  @classmethod
  def shell(cls, driver: Optional[any]=None, locals: Dict[str, any]={}):
    user = cls(driver=driver, locals=locals)
    user.present_python_shell()

  @property
  def python_locals(self) -> Dict[str, any]:
    python_locals = {}
    if self.driver is not None:
      python_locals['driver'] = self.driver
      def view_html():
        self.view_html()
      python_locals['view_html'] = view_html
    return python_locals

  def present_prompt(self, prompt: str, response_type: any=str, default_response: Optional[any]=None, prompter: Optional[Callable[[str, any, Optional[any]], any]]=None):
    if prompter is None:
      def prompter(prompt: str, response_type:any, default_response: Optional[any]) -> any:
         return click.prompt(prompt, type=response_type, default=default_response)

    if self.interactive:
      if self.timeout is None:
        response = prompter(prompt, response_type, default_response)
      elif self.timeout <= 0:
        response = default_response
      else:
        def handle_alarm(signum, frame):
          raise RaspadorInputTimeoutError()
        original_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, handle_alarm)
        original_time = time.time()
        original_alarm = signal.alarm(self.timeout)
        try:
          print(f'Will continue automaticially after {self.timeout} seconds with reponse [{default_response}]')
          response = prompter(prompt, response_type, default_response)
          signal.alarm(0)
        except RaspadorInputTimeoutError:
          print(f' => {default_response} (continuing automaticially after {self.timeout} seconds)')
          response = default_response
        signal.signal(signal.SIGALRM, original_handler)
        if original_alarm:
          new_alarm = original_alarm - round(time.time() - original_time)
          if new_alarm > 0:
            signal.alarm(new_alarm)
          else:
            signal.alarm(1)
            time.sleep(2)
    else:
      response = default_response
    return response

  def present_error(self, error: Exception):
    handler = logging.StreamHandler()
    formatter = UserExceptionFormatter()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.addHandler(handler)
    logging.exception(error)
    root.removeHandler(handler)

  def present_message(self, message: Optional[str]=None, prompt: Optional[str]=None, error: Optional[Exception]=None, response_type: any=str, default_response: Optional[any]=None):
    response = None
    if error is not None:
      self.present_error(error)
    if message is not None:
      print(message)
    if prompt is not None:
        response = self.present_prompt(prompt=prompt, response_type=response_type, default_response=default_response)
    return response

  def present_confirmation(self, prompt: str='Continue', default_response: bool=False) -> bool:
    def prompter(prompt: str, response_type: any, default_response: bool) -> bool:
      return click.confirm(prompt, default=default_response)
    return self.present_prompt(prompt=prompt, response_type=bool, default_response=default_response, prompter=prompter)

  def present_report(self, report: Union[pd.DataFrame, pd.Series], title: Optional[str]=None, prefix: Optional[str]=None, suffix: Optional[str]=None):
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):
      prefix = f'{prefix}\n' if prefix else ''
      report_text = report.to_string() if not report.empty else 'Empty report.'
      suffix = f'\n{suffix}' if suffix else ''
      self.present_title(title=title)
      self.present_message(f'{prefix}{report_text}{suffix}')

  def present_menu(self, options: List[MenuOption], default_option: Optional[MenuOption]=None, message: Optional[str]=None) -> MenuOption:
    prompt = '\n'.join([
      (o.styled + Format().underline()).styled if o is default_option else o.styled.styled for o in options
      ] + [message if message is not None else ''])
    option_values = [o.value for o in options]

    assert default_option is None or default_option in options
    assert len(option_values) == len(set(option_values)), str([o for o in options if collections.Counter(option_values)[o.value] > 1])

    choice = self.present_message(
      prompt=prompt,
      response_type=click.Choice(option_values, case_sensitive=False),
      default_response=default_option.value if default_option else None
    )
    option = next(filter(lambda o: o.value == choice, options))
    return option

  def interact(self, interaction: Interaction) -> bool:
    if interaction is Interaction.html:
      self.view_html()
    elif interaction is Interaction.image:
      # log = self.locals['log'] if 'log' in self.locals else pd.DataFrame()
      # file_name = f'{log}'
      self.save_image()
    elif interaction is Interaction.python:
      self.present_python_shell()
    elif interaction is Interaction.script:
      self.run_script()
    elif interaction is Interaction.debugger:
      self.debug()
    elif interaction is Interaction.log:
      log = self.locals['log'] if 'log' in self.locals else pd.DataFrame()
      self.present_log(log=log)

  def view_html(self):
    if self.driver is None:
      print('No driver')
      return
    time_text = self.date_file_name()
    path = os.path.join('output', 'html', f'{time_text}_{self.safe_file_name(self.driver.current_url)[:200]}.html')
    with open(path, 'w') as f:
      f.write(self.driver.page_source)
    subprocess.call([
      *user_config['view_html_command'],
      path,
    ])

  def save_image(self, file_name: Optional[str]=None, quiet: bool=False):
    def output(message: str):
      if not quiet:
        log.log(message)

    if 'browser' not in self.locals or self.locals['browser'] is None:
      output('No browser')
      return

    browser = self.locals['browser']
    if file_name is None:
      file_name = self.frame_file_name()

    source = browser.current_source
    image_path = os.path.join('output', 'image', f'{file_name}.png')
    html_path = os.path.join('output', 'html', f'{file_name}.html')
    if self.locals['browser'].save_screenshot(path=image_path):
      output(f'Image saved to {image_path}')
    else:
      output('No display')
    
    if source:
      with open(html_path, 'w') as f:
        f.write(source)
      output(f'Source saved to {html_path}')
    else:
      output('No source')

  def python_shell(self) -> str:
    if not self.interactive:
      raise RaspadorCannotInteractError()
    print('Local variables:')
    for name, value in self.locals.items():
      print(f'  {name}:\n    {pformat(value)}')
    if user_config['python_shell'].lower() == 'default':
      console = Console(locals=self.locals)
      console.interact(banner='Python shell. Type CTRL-D to exit.')
      return '\n'.join(console.record)
    elif user_config['python_shell'].lower() == 'ipython':
      print('IPython shell. Type CTRL-D to exit.')
      console = IPython.terminal.embed.InteractiveShellEmbed()
      import raspador
      console.mainloop(local_ns=self.locals, module=raspador)
      record = ''
      for index, line in enumerate(console.history_manager.input_hist_raw):
        record += f'{line}\n'
        if index in console.history_manager.output_hist:
          record += f'# {str(console.history_manager.output_hist[index])}\n'
      return record
    elif user_config['python_shell'].lower() == 'bpython':
      history_path = os.path.join('output', 'python', 'history.py')
      try:
        os.remove(history_path)
      except FileNotFoundError:
        pass
      bpython.embed(args=['--config=bpython_config'], locals_=self.locals, banner='bpython shell. Type CTRL-D to exit.')
      if os.path.isfile(history_path):
        with open(history_path, 'r') as f:
          record = f.read()
      else:
        record = ''
      return record
    else:
      raise ValueError('Invalid python_shell', user_config['python_shell'])
  
  def present_python_shell(self):
    record = self.python_shell()
    if not record.strip():
      return
    choice = click.prompt('(S)ave, (E)dit, or (D)elete record of interaction?', type=click.Choice(['s', 'e', 'd'], case_sensitive=False), default='d').lower()
    if choice in ['s', 'e', 'd']:
      path = os.path.join('output', 'python', f'{self.date_file_name()}_interaction.py')
      with open(path, 'w') as f:
        f.write(record)
      if choice == 'e':
        subprocess.call([
          *user_config['editor_command'],
          path,
        ])
        while True:
          script_name = click.prompt('To save this interaction as a script enter a script name, or press return to continue.', default='')
          if not script_name:
            break
          script_name = self.safe_file_name(script_name)
          script_path = os.path.join('output', 'python', 'scripts', f'{script_name}.py')
          if os.path.exists(script_path):
            if not click.confirm(f'A script alread exists at \'{script_path}\'\nWould you like to replace it', abort=True):
              continue
          with open(path, 'r') as f:
            with open(script_path, 'w') as g:
              g.write(f.read())
          print(f'Script written to \'{script_path}\'\nIt will be available for future use as \'{script_name}\'')
          break
      else:
        print(f'{record}\n\nWritten to {path}')

  def run_script(self, script_name: Optional[str]=None):
    script_paths = glob.glob(os.path.join('output', 'python', 'scripts', '*.py'))
    if not script_paths:
      print('No scripts found in \'output/python/scripts/\'')
      return
    script_names = {os.path.splitext(os.path.basename(p))[0]: p for p in script_paths}
    if script_name is None and self.interactive:
      default_script = self._last_script_name if self._last_script_name in script_names.keys() else None
      script_name = click.prompt('Enter a script to execute', type=click.Choice(sorted(script_names.keys())), default=default_script)
    if not script_name:
      return
    self._last_script_name = script_name
    with open(script_names[script_name], 'r') as f:
      script = f.read()
    self.run_code(code=script, file_path=script_names[script_name], description=f'from \'{script_names[script_name]}\'')

  def run_code(self, code: str, file_path: str, description: str, confirm: Optional[bool]=True):
    if confirm:
      message_style = Format().cyan()
      prompt = CustomStyled(text=f'Script...\n{"–" * 9}\n', style=message_style) + CodeStyled(text=code) + CustomStyled(text=f'{"–" * 9}\n...Script\n', style=message_style) + f'Run this script ({description})'
      if not click.confirm(prompt.styled, default=True):
        return
    compiled = compile(code, file_path, 'exec')
    exec(compiled, self.locals, self.locals)
    print(f'Ran script ({description})')    

  def debug(self):
    pdb.set_trace()

  def present_title(self, title: str=''):
    title = Format().cyan()(f'\n{title}\n{"–" * len(title)}\n') if title else ''
    print(title)

  def present_log(self, log: pd.DataFrame):
    self.present_title(title='Flight Log')
    index_style = Format().gray()
    maneuver_style = Format().bold()
    attempt_style = Format().blue()
    error_style = Format().red().bold()
    result_style = Format().green().bold()
    for index, row in log.iterrows():
      mission = f'{row.mission}.' if row.mission else ''
      print(f'{index_style(str(index))} {mission}{maneuver_style(row.maneuver)}')
      if row.error:
        print(error_style(f'  = {row.option} – {row.error}'))
      elif row.result:
        print(result_style(f'  = {row.option} : {row.result}'))
      else: 
        print(attempt_style(f'  = {row.option}'))
    print(f'{len(log)} actions logged')

  def date_file_name(self) -> str:
    return datetime.now().strftime('%Y-%m-%d_%H_%M_%S')

  def safe_file_name(self, name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '_', name)

  def frame_file_name(self) -> str:
    log = self.locals['log'] if 'log' in self.locals else pd.DataFrame()
    date_file_name = self.date_file_name()
    if log.empty:
      return date_file_name
    last_log = log.iloc[log.stable_time.values.argmax()]
    maneuvers = [
      *last_log.mission.split(" "),
      last_log.maneuver,
    ]
    last_log_text = f'{last_log.raspador}.{"." * (len(maneuvers) - 4)}{".".join(maneuvers[-4:])}'
    return f'{date_file_name}_{self.safe_file_name(name=last_log_text)[:200]}'

  def abbreviated(self, text: str, length: Optional[int]=None, ellipsis: str='...') -> str:
    if length is None:
      length = self.abbreviated_length
    if length == 0:
      return ''
    if length < 0 or len(text) <= length:
      return text
    abbreviated_text = f'{text[:int(length / 2)]}{ellipsis}{text[int(length / 2) - length + len(ellipsis):]}'
    if len(abbreviated_text) > length:
      abbreviated_text = abbreviated_text[:length]
    return abbreviated_text