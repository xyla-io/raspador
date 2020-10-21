import json
import importlib

from pathlib import Path
from typing import Optional, Dict, Callable
from io_map import IOMap
from .maneuver import Maneuver, OrdnanceManeuver
from .pilot import Pilot
from .raspador import Raspador
from .user_interactor import UserInteractor
from .browser_interactor import BrowserInteractor
from .error import RaspadorBotError

class BotManeuver(OrdnanceManeuver[Pilot, Raspador]):
  bot_name: Optional[str]
  configuration_name: str
  configuration: Dict[str, any]
  browser: Optional[BrowserInteractor]
  user: Optional[UserInteractor]
  clear_context: bool

  def __init__(self, bot_name: Optional[str]=None, configuration_name: Optional[str]='default', configuration: Dict[str, any]={}, browser: Optional[BrowserInteractor]=None, user: Optional[UserInteractor]=None, clear_context: bool=True):
    self.bot_name = bot_name
    self.configuration_name = configuration_name
    self.configuration = configuration
    self.browser = browser
    self.user = user
    self.clear_context = clear_context

    super().__init__()

  def attempt(self, pilot: Pilot, fly: Callable[[Maneuver], Maneuver], scraper: Raspador):
    configuration_path = Path(__file__).parent.parent / 'configurations' / f'{self.bot_name}_configuration' / f'{self.bot_name}_configuration_{self.configuration_name}.json'
    configuration = json.loads(configuration_path.read_bytes()) if configuration_path.exists() else {}
    configuration.update(self.configuration)
    module = importlib.import_module(self.bot_name)
    try:
      with IOMap._local_registries(clear=self.clear_context):
        bot: Raspador = module.Bot(
          browser=pilot.browser if self.browser is None else self.browser,
          user=self.user,
          configuration=configuration,
          interactive=pilot.user.interactive if self.user is None else None
        )
        if self.user is None:
          self.configure_user(
            source_user=pilot.user,
            target_user=bot.user
          )
        bot.scrape()
    finally:
      if self.browser is not None:
        bot.browser.driver.quit()

    bot_log = bot.flight_logs[-2]
    scraper.flight_logs[-1] = scraper.flight_logs[-1].append(bot_log)
    bot_error = bot_log.iloc[-1].error
    if bot_error:
      raise RaspadorBotError(
        bot=bot,
        bot_error=bot_error
      )
    self.load(bot)

  def configure_user(self, source_user: UserInteractor, target_user: UserInteractor):
    target_user.interactive = source_user.interactive
    target_user.control_mode = source_user.control_mode
    target_user.timeout = source_user.timeout
    target_user.abbreviated_length = source_user.abbreviated_length
    target_user.break_on_exceptions = source_user.break_on_exceptions
    target_user.monitor = source_user.monitor
    target_user.retry = source_user.retry

