from .base import MenuOption, Ordnance
from .browser_interactor import BrowserInteractor
from .user_interactor import UserInteractor
from typing import Optional, TypeVar, Generic
from datetime import datetime

class Pilot:
  browser: BrowserInteractor
  user: UserInteractor
  born: datetime

  def __init__(self, browser: BrowserInteractor, user: UserInteractor):
    self.browser = browser
    self.user = user
    self.born = datetime.utcnow()

  @property
  def description(self) -> str:
    return self.name

  @property
  def name(self) -> str:
    return type(self).__name__

  def __getitem__(self, key: str) -> any:
    return getattr(self, key)

  def __setitem__(self, key: str, value: any):
    setattr(self, key, value)

  def __delitem__(self, key):
    delattr(self, key)

O = TypeVar(any)
class OrdnancePilot(Generic[O], Ordnance[O], Pilot):
  no_ordnance_values = []
