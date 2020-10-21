import os
import sys
import pdb
import bdb
import click
import logging
import signal
import hashlib
import inspect
import traceback
import pandas as pd

from subir import Uploader
from .browser_interactor import BrowserInteractor
from .user_interactor import UserInteractor, Interaction
from .pilot import Pilot
from .maneuver import Maneuver, Position, InteractQueueManeuver, BreakManeuver
from .base import MenuOption, ControlMode, ControlAction, Ordnance
from .error import RaspadorDidNotCompleteManuallyError, RaspadorInvalidManeuverError, RaspadorInvalidPositionError, RaspadorInteract, RaspadorSkip, RaspadorSkipOver, RaspadorSkipUp, RaspadorSkipToBreak, RaspadorQuit, RaspadorUnexpectedResultsError
from .style import Format, Styled
from .parser import Parser
from data_layer import Redshift as SQL
from typing import Dict, List, Optional, TypeVar, Generic, Union
from enum import Enum
from io_map import IOMap

class Raspador(IOMap):
  browser: BrowserInteractor
  user: UserInteractor
  configuration: Dict[str, any]
  flight_logs: List[pd.DataFrame]

  def __init__(self, browser: Optional[BrowserInteractor]=None, user: Optional[UserInteractor]=None, configuration: Dict[str, any]=None, interactive: Optional[bool]=None):
    self.configuration = configuration if configuration else {}
    self.browser = browser if browser else BrowserInteractor()
    self.user = user if user else UserInteractor(driver=self.browser.driver)
    self.flight_logs = [pd.DataFrame()]
    if interactive is not None:
      self.user.interactive = interactive

  @property
  def description(self) -> str:
    return self.name

  @property
  def name(self) -> str:
    return type(self).__name__

  @property
  def flight_log(self) -> pd.DataFrame:
    return self.flight_logs[-1]

  @flight_log.setter
  def flight_log(self, flight_log: pd.DataFrame):
    self.flight_logs[-1] = flight_log

  @property
  def top_maneuvers_report(self) -> pd.DataFrame:
    report = self.flight_log[['maneuver', 'option', 'result']].groupby(['maneuver', 'option', 'result']).size()
    return report

  @property
  def top_errors_report(self) -> pd.DataFrame:
    report = self.flight_log[self.flight_log.error != ''][['error', 'maneuver']].groupby(['error', 'maneuver']).size()
    return report

  def scrape(self):
    if not self.flight_log.empty:
      self.user.present_report(report=self.top_maneuvers_report, title='Mission Report')
      self.user.present_report(self.top_errors_report, title='Error Report')
      self.save_log()
      unexpected_results = list(filter(lambda r: r not in ['Completed', ''], self.flight_log.result.unique()))
      if unexpected_results:
        unexpected_results_error = RaspadorUnexpectedResultsError(unexpected_results=unexpected_results)
        if self.user.interactive:
          self.user.present_message('Unexpected results.', error=unexpected_results_error)
        else:
          raise unexpected_results_error
      self.flight_logs.append(pd.DataFrame())

  def run(self):
    self.scrape()

  def fly(self, pilot: Pilot, maneuver: Maneuver, mission: List[Maneuver]=[]):
    option = None
    error = None
    position = None
    while True:
      try:
        if self.user.monitor:
          self.user.locals = {
            'log': self.flight_log,
            'browser': pilot.browser,
            **self.user.python_locals,
          }
          self.user.save_image(file_name='monitor', quiet=True)
          self.user.locals = self.user.python_locals
        if not isinstance(maneuver, Maneuver):
          raise RaspadorInvalidManeuverError(maneuver=maneuver)
        self.user.present_message(f'{self.mission_description(pilot=pilot, mission=mission, maneuver=maneuver)}')
        option = self.select_option(
          maneuver=maneuver, 
          option=option, 
          error=error, 
          message=f'{self.break_description(pilot=pilot, maneuver=maneuver, mission=mission)}\n'
        )
        if isinstance(option, ControlMode):
          self.user.control_mode = option
        position = Position(option=option).enter()
        maneuver.trajectory.append(position)
        self.attempt_option(pilot=pilot, maneuver=maneuver, mission=mission, error=error)
        error = None
      except KeyboardInterrupt as e:
        error = e
        if self.user.present_confirmation('Abort', default_response=True):
          self.user.interactive = False
          raise
      except (RaspadorDidNotCompleteManuallyError, RaspadorInteract, RaspadorSkip, click.Abort) as e:
        error = e
      except Exception as e:
        stack_format = traceback.format_stack()
        _, _, trace_back = sys.exc_info()
        error = e
        newline = '\n'
        empty_string = ''
        self.user.present_message(
          message=f'{self.mission_description(pilot=pilot, mission=mission)}\n{Format().yellow()(f"Error encountered at{newline}{empty_string.join(stack_format)}")}',
        )
        self.user.present_message(error=error)
        present_postmortem = self.user.break_on_exceptions or self.user.present_confirmation(prompt='Start postmortem')
        if present_postmortem:
          try:
            while True:
              self.user.present_message(message=self.catch_description(pilot=pilot, maneuver=maneuver, mission=mission, error=error, is_postmortem=True))
              pdb.post_mortem(t=trace_back)
              self.user.present_message(message=self.catch_description(pilot=pilot, maneuver=maneuver, mission=mission, error=error, is_postmortem=False))
              pdb.set_trace()
              if not self.user.present_confirmation(prompt='Repeat postmortem'):
                break
          except bdb.BdbQuit as pdb_error:
            error = pdb_error
      finally:
        if isinstance(error, click.Abort):
          raise error
        if position is None:
          raise RaspadorInvalidPositionError(position=position, maneuver=maneuver, error=error)
        position.stabilize(error=error)
        position = None
        self.record_position(pilot=pilot, maneuver=maneuver, mission=mission)
        maneuver.clear_run(force=True)
        if not self.flight_control(option=option, error=error, maneuver=maneuver, mission=mission):
          break
        if maneuver.status.finished:
          self.user.present_message(f'{self.mission_description(pilot=pilot, mission=mission, maneuver=maneuver, reverse=True)}')
          if self.user.control_mode is ControlMode.step_next and self.user.control_mode in maneuver.options:
            break_maneuver = BreakManeuver(maneuver=maneuver)
            self.fly(pilot=pilot, maneuver=break_maneuver, mission=mission + [maneuver])
          break
  
  def flight_control(self, option: MenuOption, error: Optional[Exception], maneuver: Maneuver, mission: List[Maneuver]) -> bool:
    if option is ControlMode.step_over:
      self.user.control_mode = ControlMode.step_next
    elif option is ControlMode.step_up:
      self.user.control_mode = ControlMode.step_over
    elif option is ControlMode.step_break and not mission:
      self.user.control_mode = ControlMode.step_next
    
    if isinstance(error, RaspadorQuit) or isinstance(error, bdb.BdbQuit):
      if mission:
        raise RaspadorQuit(maneuver=maneuver)
      else:
        return False
    elif isinstance(error, RaspadorSkip) and not mission:
      self.user.control_mode = ControlMode.step_next
    elif isinstance(error, RaspadorSkipUp):
        raise RaspadorSkipOver(maneuver=maneuver)
    elif isinstance(error, RaspadorSkipToBreak):
        raise RaspadorSkipToBreak(maneuver=maneuver)
    return True

  def record_position(self, pilot: Pilot, maneuver: Maneuver, mission: List[Maneuver]=[]):
    position = maneuver.position
    if position is None:
      return
    self.flight_log = self.flight_log.append([
      {
        'entry_time': position.entry_time.isoformat(),
        'stable_time': position.stable_time.isoformat(),
        'raspador': self.name,
        'pilot': pilot.name,
        'mission': ' '.join(m.name for m in mission),
        'maneuver': maneuver.name,
        'option': position.option.option_text,
        'error': type(position.error).__name__ if position.error is not None else '',
        'detail': '' if self.user.abbreviated_length == 0 else self.user.abbreviated(str(maneuver)),
        'result': maneuver.status.value if maneuver.status.finished else '',
        'instruction': '' if self.user.abbreviated_length == 0 else self.user.abbreviated(maneuver.instruction),
        'id': repr(position.id),
        'maneuver_id': repr(maneuver.id),
        'mission_id': '.'.join(repr(m.id) for m in mission),
      }
    ])
  
  def attempt_option(self, pilot: Pilot, maneuver: Maneuver, mission: List[Maneuver], error: Optional[Exception]=None):
    if isinstance(maneuver.position.option, ControlMode):
      fly_mission = mission + [maneuver]
      def fly(maneuver: Maneuver) -> Maneuver:
        self.fly(pilot=pilot, maneuver=maneuver, mission=fly_mission)
        return maneuver
      attempt_arguments = {
        'pilot': pilot,
        'fly': fly,
        'scraper': self,
      }
      type(self)._register_context(attempt_arguments)
      attempt_signature = inspect.getfullargspec(maneuver.attempt_manually if maneuver.position.option is ControlMode.manual else maneuver.attempt)
      if not attempt_signature.varkw:
        if len(attempt_signature.args) < 4:
          del attempt_arguments['scraper']
        if len(attempt_signature.args) < 3:
          del attempt_arguments['fly']
      if maneuver.position.option is ControlMode.manual:
        self.user.present_message(self.detail_description(detail=maneuver.detail))
        attempt = maneuver.attempt_manually(**attempt_arguments)
      else:
        attempt = maneuver.attempt(**attempt_arguments)
      if attempt is not None:
        try:
          submaneuver = next(attempt)
          while submaneuver is not None:
            self.fly(pilot=pilot, maneuver=submaneuver, mission=mission + [maneuver])
            submaneuver = attempt.send(submaneuver)
        except StopIteration as e:
          submaneuver = e.value
        if submaneuver is not None:
          self.fly(pilot=pilot, maneuver=submaneuver, mission=mission + [maneuver])
    elif maneuver.position.option is ControlAction.repair_environment:
      maneuver.abort(error=error)
    elif maneuver.position.option is ControlAction.quit:
      self.user.present_message('Qutting.')
      raise RaspadorQuit(maneuver=maneuver)  
    elif isinstance(maneuver.position.option, Interaction):
      sequence_maneuver = InteractQueueManeuver()
      def enqueue_maneuver(maneuver: Maneuver):
        sequence_maneuver.append(maneuver)
      self.user.locals = {
        'log': self.flight_log,
        'pilot': pilot,
        'browser': pilot.browser,
        'parser': Parser.from_browser(browser=pilot.browser),
        'maneuver': maneuver,
        'mission': mission,
        'scraper': self,
        'maneuver_queue': sequence_maneuver,
        'enqueue_maneuver': enqueue_maneuver,
        'inspect_source': inspect.getsource,
        'inspect': inspect,
        **self.user.python_locals,
      }
      self.user.interact(interaction=maneuver.position.option)
      self.user.locals = self.user.python_locals
      if not sequence_maneuver.empty:
        try:
          self.fly(pilot=pilot, maneuver=sequence_maneuver, mission=mission)
        except RaspadorSkipToBreak:
          pass
        finally:
          if self.user.control_mode is ControlMode.step_break:
            self.user.control_mode = ControlMode.step_next
    elif maneuver.position.option is ControlAction.skip_over:
      raise RaspadorSkipOver(maneuver=maneuver)
    elif maneuver.position.option is ControlAction.skip_up:
      raise RaspadorSkipUp(maneuver=maneuver)
    elif maneuver.position.option is ControlAction.skip_break:
      raise RaspadorSkipToBreak(maneuver=maneuver)

  def select_option(self, maneuver: Maneuver, option: Optional[MenuOption], error: Optional[Exception]=None, message: Optional[str]=None):
    options = maneuver.options
    default_option = self.default_option(maneuver=maneuver, option=option, error=error)
    if default_option not in options:
      options.append(default_option)
    if ControlAction.quit not in options:
      options.append(ControlAction.quit)

    if error is None and default_option is self.user.control_mode and default_option not in [ControlMode.step_next, ControlMode.manual]:
      return default_option
    else:
      return self.user.present_menu(options=maneuver.options, default_option=default_option, message=message)

  def default_option(self, maneuver: Maneuver, option: Optional[MenuOption], error: Optional[Exception]=None) -> MenuOption:
    if error is not None and self.user.retry is not None and len([p for p in maneuver.trajectory if p.error]) > self.user.retry and ControlAction.skip_up in maneuver.options:
      return ControlAction.skip_up
    if error is not None and ControlAction.repair_environment in maneuver.options:
        return ControlAction.repair_environment
    if isinstance(option, Interaction) and option in maneuver.options:
      return option
    if self.user.control_mode in maneuver.options:
      return self.user.control_mode
    for control_mode in ControlMode:
      if control_mode in maneuver.options:
        return control_mode
    return ControlAction.quit

  def mission_description(self, pilot: Pilot, mission: List[Maneuver], maneuver: Optional[Maneuver]=None, reverse: bool=False) -> str:
    context = [
      self.description,
      pilot.description,
      *[self.maneuver_description(maneuver=m) for m in mission],
    ]
    context = [Format().color(white=0.2 + (i + 1) / len(context) * 0.4)(c) for i, c in enumerate(context)]
    if maneuver:
      context.append(
        f'{self.maneuver_description(maneuver)}: {maneuver.status.value}...' if not reverse else f'{self.maneuver_description(maneuver)}: ...{maneuver.status.value}'
      )
    context = [
      '–' * (i + 1) + '> ' + c
      for i, c in enumerate(context)
    ]
    if reverse:
      context = reversed(context)
    return '\n'.join(context)

  def detail_description(self, detail: Union[Styled, List[any]], level: int=0):
    if not isinstance(detail, list):
      return detail.styled

    detail_format = Format().cyan()
    return detail_format('Steps:\n') + '\n'.join([
      detail_format(f'{"–" * level} {i + 1}. ') + self.detail_description(detail=d, level=level + 1)
      for i, d in enumerate(detail)
    ])
    
  def maneuver_description(self, maneuver: Maneuver) -> str:
    description = maneuver.instruction
    if maneuver.position is not None:
      description += f' <{maneuver.position.option.option_text}>'
    return description

  def break_description(self, pilot: Pilot, maneuver: Maneuver, mission: List[Maneuver]) -> str:
    break_format = Format().magenta()
    mission_text = f'Breaking at {".".join([self.name, pilot.name] + [m.name for m in mission])}'
    detail_styled = break_format + f'({maneuver.instruction}'
    if maneuver.position:
      detail_styled += break_format + ' after '
      detail_styled += break_format.bold() + maneuver.position.description
    detail_styled += break_format + ')'
    return f'{break_format(mission_text)}.{break_format.bold()(maneuver.name)}\n{detail_styled.styled}'

  def catch_description(self, pilot: Pilot, maneuver: Maneuver, mission: List[Maneuver], error: Exception, is_postmortem: bool=True) -> str:
    catch_format = Format().yellow()
    mission_text = f'Caught exception {type(error).__name__} at {".".join([self.name, pilot.name] + [m.name for m in mission])}'
    detail_styled = catch_format + f'({maneuver.instruction}'
    detail_styled += catch_format + ')'
    stack_styled = catch_format + ('Postmortem envionment.' if is_postmortem else 'Post-postmortem environment.')
    if not is_postmortem:
      detail_styled += catch_format + ' after postmortem'
    return f'{catch_format(mission_text)}.{catch_format.bold()(maneuver.name)}\n{detail_styled.styled}\n{stack_styled.styled}'

  def save_log(self):
    path = os.path.join('output', 'log', f'{self.user.date_file_name()}_{self.user.safe_file_name(self.description)}.csv')
    if self.flight_log.empty:
      self.user.present_message(f'No log to save to \'{path}\'')
      return
    
    self.flight_log.to_csv(path)
    self.user.present_message(f'Saved {len(self.flight_log)} log rows to \'{path}\'')

O = TypeVar(any)
class OrdnanceRaspador(Generic[O], Raspador, Ordnance[O]):
  def run(self):
    super().run()
    return self.ordnance
  
class ReportRaspador(OrdnanceRaspador[pd.DataFrame]):
  output_file_name: str
  output_file_directory: str

  def __init__(self, output_file_name: Optional[str]=None, output_file_directory: Optional[str]=None, browser: Optional[BrowserInteractor]=None, user: Optional[UserInteractor]=None, configuration: Dict[str, any]=None, interactive: Optional[bool]=None):
    super().__init__(browser=browser, user=user, configuration=configuration, interactive=interactive)
    self.output_file_name = output_file_name if output_file_name is not None else f'{self.user.date_file_name()}_{self.user.safe_file_name(self.description)}'
    self.output_file_directory = output_file_directory if output_file_directory else os.path.join('output', 'csv')

  def scrape(self):
    super().scrape()
    self.save_output()

  def save_output(self):
    if not self.output_file_name:
      return

    path = os.path.join(self.output_file_directory, f'{self.output_file_name}.csv')
    if self.ordnance is None or self.ordnance.empty:
      self.user.present_message(f'No data to save to \'{path}\'')
      return
    
    self.ordnance.to_csv(path)
    self.user.present_message(f'Saved {len(self.ordnance)} data rows to \'{path}\'')

class UploadReportRaspador(ReportRaspador):
  schema: str
  table: str
  confirm_upload: bool

  @property
  def merge_on_columns(self) -> List[str]:
    return []

  @property
  def column_types(self) -> Dict[str, any]:
    return {}

  @property
  def replace(self) -> bool:
    return False

  def __init__(self, schema: str, table: str, confirm_upload: bool=True, output_file_name: Optional[str]=None, output_file_directory: Optional[str]=None, browser: Optional[BrowserInteractor]=None, user: Optional[UserInteractor]=None, configuration: Dict[str, any]=None, interactive: Optional[bool]=None):
    self.schema = schema
    self.table = table
    self.confirm_upload=confirm_upload
    super().__init__(
      output_file_name=output_file_name,
      output_file_directory=output_file_directory,
      browser=browser,
      user=user,
      configuration=configuration,
      interactive=interactive
    )

  def scrape(self):
    super().scrape()
    self.upload()

  def upload(self):
    if self.ordnance is None or self.ordnance.empty:
      self.user.present_message(f'No data to upload to table\'{self.table}\' in schema \'{self.schema}\'')
      return
    
    if self.confirm_upload and not self.user.present_confirmation(f'Confirm data upload to table \'{self.table}\' in schema \'{self.schema}\'', default_response=True):
        return

    uploader = Uploader()
    uploader.upload_data_frame(schema_name=self.schema, table_name=self.table, merge_column_names=self.merge_on_columns, data_frame=self.ordnance, column_type_transform_dictionary=self.column_types, replace=self.replace)
    self.user.present_message(f'Uploaded {len(self.ordnance)} rows to table\'{self.table}\' in schema \'{self.schema}\'')
