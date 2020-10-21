from raspador import Pilot, UserInteractor, BrowserInteractor
from typing import Dict, List
from pathlib import Path

class MapGraphPilot(Pilot):
  config: Dict[str, any]
  sign_in_wait = 3.0

  def __init__(self, config: Dict[str, any], user: UserInteractor, browser: BrowserInteractor):
    self.config = config
    super().__init__(user=user, browser=browser)
  
  @property
  def entry_key(self) -> str:
    return self.config['entry_key']

  @property
  def map_context_urls(self) -> List[str]:
    return self.config['map_context_urls']
  
  @property
  def base_url(self) -> str:
    url = self.config['base_url']
    if url.startswith('.'):
      url = f'file://{Path(__file__).resolve().parent.parent.parent / url}'
    return url