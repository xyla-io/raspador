from .raspador import Raspador
from .maneuver import Maneuver, NavigationManeuver, InteractManeuver
from .pilot import Pilot
from typing import Optional, Generator

class FinishExploringManeuver(Maneuver):
  def attempt(self, pilot: Pilot):
    pass

class ExploreManeuver(Maneuver):
  url: str
  
  def __init__(self, url: str):
    self.url = url
    super().__init__()

  def attempt(self, pilot: Pilot) -> Optional[Generator[Optional[Maneuver], Maneuver, Optional[Maneuver]]]:
    navigate = yield NavigationManeuver[Pilot](url=self.url)
    self.require(navigate)
    yield InteractManeuver()
    return FinishExploringManeuver()

class ExploreScraper(Raspador):
  def scrape(self):
    pilot = Pilot(browser=self.browser, user=self.user)
    maneuver = ExploreManeuver(url=self.configuration['url'])
    self.fly(pilot=pilot, maneuver=maneuver)
    super().scrape()