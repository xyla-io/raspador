import click
import signal
import os
import sys
import json
import shutil
import importlib
import subprocess

from data_layer import Redshift as SQL
from config import sql_config
from raspador import ExploreScraper, ControlMode, UserInteractor, Styling, Element, RaspadorQuit, QuitManeuver
from typing import Optional, Tuple
from credentials import raspador_slackbot_credentials
from pathlib import Path
from moda.user import UserInteractor
from moda.style import Format, CustomStyled, Styleds

all_database_values = sql_config.keys()

class Scrape:
  database_name: str
  interactivity: int
  detail_length: int
  break_on_exceptions: bool
  monitor: bool
  retry: Optional[int]

  def __init__(self, database_name:str, interactivity: int=0, detail_length: int=2048, break_on_exceptions: bool=False, monitor: bool=False, retry: Optional[int]=None):
    self.database_name = database_name
    self.interactivity = interactivity
    self.detail_length = detail_length
    self.break_on_exceptions = break_on_exceptions
    self.monitor = monitor
    self.retry = retry

  def configure_user_interactivity(self, user: UserInteractor):
    user.interactive = self.interactivity > 0
    if self.interactivity > 1:
      user.control_mode = ControlMode.step_next
      if self.interactivity > 2:
        user.timeout = None
    user.abbreviated_length = self.detail_length
    user.break_on_exceptions = self.break_on_exceptions
    user.monitor = self.monitor
    user.retry = self.retry

def validate_retry(ctx, param, value):
  if not value:
    return None
  try:
    retry = int(value)
    if retry < 0:
      raise ValueError(value)
    return retry
  except ValueError:
    raise click.BadParameter('retry must be a nonnegative integer')

@click.group()
@click.option('-db', '--database', 'database_name', type=click.Choice(all_database_values), default='default')
@click.option('-i', '--interactive', 'interactivity', count=True)
@click.option('-p/-P', '--pretty/--no-pretty', 'pretty', default=True)
@click.option('-h/-H', '--highlight/--no-highlight', 'highlight', default=False)
@click.option('--pdb/--no-pdb', 'break_on_exceptions', default=False)
@click.option('--monitor/--no-monitor', 'monitor', default=False)
@click.option('-r', '--retry', 'retry', type=str, default='', callback=validate_retry)
@click.option('-t', '--timeout', 'timeout', type=int, default=60 * 60 * 48)
@click.option('-l', '--detail-length', 'detail_length', type=int, default=2048)
@click.pass_context
def run(ctx: any, database_name: str, interactivity, pretty: bool, highlight: bool, break_on_exceptions: bool, monitor: bool, retry: Optional[int], timeout: int, detail_length: int):
  ctx.obj = Scrape(database_name=database_name, interactivity=interactivity, detail_length=detail_length, break_on_exceptions=break_on_exceptions, monitor=monitor, retry=retry)
  SQL.Layer.configure_connection(sql_config[ctx.obj.database_name])
  Styling.enabled = pretty
  Element.highlight_enabled = highlight
  if timeout > 0:
    def handle_timeout(signum, frame):
      print(f'Timeout of {timeout} seconds reached. Quitting.')
      raise RaspadorQuit(maneuver=QuitManeuver())
    signal.signal(signal.SIGALRM, handle_timeout)
    signal.alarm(timeout)

@run.group()
def bot():
  pass

@bot.command()
@click.option('-n', '--nickname', type=str)
@click.option('-p', '--prefix', type=str)
@click.option('-t', '--type-prefix', type=str)
@click.option('-td', '--template-directory', type=click.Path(exists=True, dir_okay=True, file_okay=False, readable=True))
@click.option('-tp', '--template-prefix', type=str)
@click.option('-tt', '--template-type-prefix', type=str)
@click.option('-i/-I', '--install/--no-install', 'should_install', is_flag=True, default=True)
@click.argument('project')
@click.pass_obj
@click.pass_context
def init(ctx: any, scrape: Scrape, project: str, nickname: Optional[str], prefix: Optional[str], type_prefix: Optional[str], template_directory: Optional[str], template_prefix: Optional[str], template_type_prefix: Optional[str], should_install: bool):
  if not nickname:
    nickname = project
  if not prefix:
    prefix = project
  if not type_prefix:
    type_prefix = ''.join(s.title() for s in project.split('_'))
  if not template_directory:
    template_directory = str(Path(__file__).parent / 'bots' / 'raspador_template')
  if not template_prefix:
    template_prefix = 'raspador_template'
  if not template_type_prefix:
    template_type_prefix = 'RaspadorTemplate'

  # Make sure that installation will succeed
  if should_install:
    ctx.invoke(
      bot_install,
      project=project,
      nickname=nickname,
      _dry_run=True
    )

  project_path = Path(__file__).parent / 'bots' / project
  user = UserInteractor()
  scrape.configure_user_interactivity(user=user)
  if project_path.exists():
    user.present_message(Format().red()(f'Project path {project_path} already exists'))
    raise click.Abort()
  template_path = Path(template_directory)
  if not template_path.exists():
    user.present_message(Format().red()(f'Template path {template_path} does not exist'))
    raise click.Abort()
  template_name = template_path.name

  shutil.copytree(str(template_path), str(project_path))
  for root, directories, files in os.walk(str(project_path), topdown=False):
    if Path(root).name == '__pycache__':
      continue
    for file in files:
      template_file_path = Path(root) / file
      if template_file_path.suffix == '.pyc':
        template_file_path.unlink()
        continue
      if not template_file_path.name.startswith(template_prefix) and template_file_path.name != '__init__.py':
        continue
      template_text = template_file_path.read_text()
      file_path = template_file_path.parent / template_file_path.name.replace(template_name, project)
      template_file_path.rename(file_path)
      text = template_text.replace(template_prefix, prefix).replace(template_type_prefix, type_prefix)
      file_path.write_text(text)
    for directory in directories:
      template_directory_path = Path(root) / directory
      if not template_directory_path.name.startswith(template_prefix):
        continue
      directory_path = template_directory_path.parent / template_directory_path.name.replace(template_name, project)
      template_directory_path.rename(directory_path)

  user.present_message(Styleds([
    CustomStyled(f'Created the ', Format().green()),
    CustomStyled(project, Format().green().bold()),
    CustomStyled(f' project at\n{project_path}', Format().green()),
  ]).styled)

  if should_install:
    ctx.invoke(
      bot_install,
      project=project,
      nickname=nickname,
    )
  else:
    user.present_message(Styleds([
      CustomStyled(f'Install the ', Format().green()),
      CustomStyled(project, Format().green().bold()),
      CustomStyled(f' bot with the command\n> {Path(__file__).parent.resolve() / "run.sh"} bot install {project}', Format().green()),
    ]).styled)

@bot.command(name='install')
@click.option('-i/-I', '--run-install-script/--no-run-install-script', 'should_run_install', is_flag=True, default=True)
@click.option('-c/-C', '--config/--no-config', 'should_copy_configuration', is_flag=True, default=True)
@click.option('-s/-S', '--script-link/--no-script-link', 'should_link_script', is_flag=True, default=True)
@click.option('-n', '--nickname')
@click.option('-u', '--url')
@click.argument('project')
@click.pass_obj
def bot_install(scrape: Scrape, project: str, should_run_install: bool=True, should_copy_configuration: bool=True, should_link_script: bool=True, nickname: Optional[str]=None, url: Optional[str]=None, _dry_run: bool=False):
  assert url is None, 'Installing from a URL is not yet supported'

  if not nickname:
    nickname = project

  project_path = Path(__file__).parent / 'bots' / project
  user = UserInteractor()
  scrape.configure_user_interactivity(user=user)
  if not _dry_run and not project_path.exists():
    user.present_message(Format().red()(f'Project path {project_path} does not exist'))
    raise click.Abort()
  configuration_path = Path(__file__).parent / 'configurations' / f'{project}_configuration'
  if should_copy_configuration and configuration_path.exists():
    user.present_message(Format().red()(f'Configuration path {configuration_path} already exists'))
    raise click.Abort()
  script_path = Path(__file__).parent / 'output' / 'python' / 'scripts' / f'{nickname}.py'
  if should_link_script and script_path.exists():
    user.present_message(Format().red()(f'Script link path {script_path} already exists'))
    raise click.Abort()

  if _dry_run:
    return

  if should_run_install:
    install_path = project_path / 'install.sh'
    if install_path.exists():
      subprocess.call(
        args=[
          './install.sh'
        ],
        cwd=str(install_path.parent)
      )
      user.present_message(CustomStyled(f'\nRan the install script at \n{install_path}', Format().yellow()).styled)

  if should_copy_configuration:
    configuration_source_path = project_path / f'{project}_configuration'
    if configuration_source_path.exists():
      shutil.copytree(str(configuration_source_path), str(configuration_path))
      configuration_path.chmod(0o700)
      user.present_message(CustomStyled(f'\nAdded a configuration directory at\n> {configuration_path}\nSet local configuration options here', Format().blue()).styled)
  
  if should_link_script:
    script_source_path = project_path / f'{project}_maneuver.py'
    if script_source_path.exists():
      relative_path = os.path.relpath(str(script_source_path.absolute()), str(script_path.parent.absolute()))
      script_path.symlink_to(relative_path)
      user.present_message(CustomStyled(f'\nAdded a script symlink at\n{script_path} to\n> {script_source_path}\nImplement the bot\'s maneuevers here', Format().cyan()).styled)

  user.present_message(Styleds([
    CustomStyled(f'\nRun the ', Format().green()),
    CustomStyled(project, Format().green().bold()),
    CustomStyled(f' bot with the command\n> {Path(__file__).parent.resolve() / "run.sh"} -i bot start {project} default', Format().green()),
  ]).styled)

@bot.command(name='remove')
@click.option('-c/-C', '--config/--no-config', 'should_remove_configuration', is_flag=True, default=True)
@click.option('-s/-S', '--script-link/--no-script-link', 'should_remove_script_link', is_flag=True, default=True)
@click.argument('project')
@click.pass_obj
def bot_remove(scrape: Scrape, should_remove_configuration: bool, should_remove_script_link: bool, project: str):
  user = UserInteractor()
  scrape.configure_user_interactivity(user=user)
  project_path = Path(__file__).parent / 'bots' / project
  if not user.present_confirmation(f'Remove the {project} bot and all of its files at {project_path}', default_response=True):
    return
  paths = []
  if project_path.exists():
    paths.append(project_path)
  if should_remove_configuration:
    configuration_path = Path(__file__).parent / 'configurations' / f'{project}_configuration'
    if configuration_path.exists():
      paths.append(configuration_path)
  if should_remove_script_link:
    scripts_path = Path(__file__).parent / 'output' / 'python' / 'scripts'
    for root, _, files in os.walk(str(scripts_path), topdown=False):
      for file in files:
        path = Path(root) / file
        if path.is_symlink() and project_path.absolute() in path.resolve().parents:
          paths.append(path)

  if paths:
    base_path = Path(__file__).parent
    user.present_message(Styleds([
      CustomStyled(f'Discovered {len(paths)} directories and files related to bot ', Format().yellow()),
      CustomStyled(project, Format().yellow().bold()),
      CustomStyled(f'\n{" ".join([str(p.relative_to(base_path)) for p in paths])}', Format().red()),
      CustomStyled(f'\nPlease remove them manually', Format().yellow()),
    ]).styled)
  else:
    user.present_message(Styleds([
      CustomStyled(f'No files discovered related to bot ', Format().yellow()),
      CustomStyled(project, Format().yellow().bold()),
    ]).styled)

@bot.command(
  context_settings={
    'ignore_unknown_options': True,
  },
  name='start'
)
@click.argument('bot_options', nargs=-1, type=click.UNPROCESSED)
@click.argument('project')
@click.argument('configuration')
@click.pass_obj
def bot_start(scrape: Scrape, bot_options: Tuple[str], project: str, configuration: str):
  configuration_path = Path(__file__).parent / 'configurations' / f'{project}_configuration' / f'{project}_configuration_{configuration}.json'
  if len(bot_options) % 2:
    user = UserInteractor()
    scrape.configure_user_interactivity(user=user)
    user.present_message('Scrape options must have the form [-[-]]OPTION VALUE [[-[-]]OPTION VALUE] ... PROJECT')
    raise click.Abort()
  configuration = json.loads(configuration_path.read_bytes()) if configuration_path.exists() else {}
  for index, option in enumerate(bot_options):
    if index % 2:
      continue
    for _ in range(2):
      if option.startswith('-'):
        option = option[1:]
    configuration[option] = bot_options[index + 1]
  sys.path.append(str(Path(__file__).parent / 'bots'))
  module = importlib.import_module(project)
  bot = module.Bot(configuration=configuration, interactive=scrape.interactivity > 0)
  scrape.configure_user_interactivity(user=bot.user)
  try:
    bot.scrape()
  finally:
    bot.browser.driver.quit()

@run.command()
@click.argument('url', default='https://example.com')
@click.pass_obj
def explore(scrape: Scrape, url: str):
  scraper = ExploreScraper(configuration={'url': url}, interactive=scrape.interactivity > 0)
  scrape.configure_user_interactivity(user=scraper.user)
  try:
    scraper.scrape()
  finally:
    scraper.browser.driver.quit()

if __name__ == '__main__':
  run()