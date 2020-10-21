from raspador import Pilot, UserInteractor, BrowserInteractor
from typing import Dict, List

class RaspadorTemplatePilot(Pilot):
  config: Dict[str, any]
  sign_in_wait = 3.0

  def __init__(self, config: Dict[str, any], user: UserInteractor, browser: BrowserInteractor):
    self.config = config
    super().__init__(user=user, browser=browser)
  
  @property
  def email(self) -> str:
    return self.config['email']

  @property
  def password(self) -> str:
    return self.config['password']
  
  @property
  def base_url(self) -> str:
    return self.config['base_url']