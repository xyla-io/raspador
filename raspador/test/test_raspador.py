import pytest
from raspador import Raspador, Pilot, Maneuver
from typing import Optional, Generator

class TPilot(Pilot):
  pass

class TNavigationManeuver(Maneuver):
  def attempt(self, pilot: TPilot):
    pilot.browser.navigate('https://example.com/')

class TElementManeuver(Maneuver):
  element: Optional[any]

  def attempt(self, pilot: TPilot) -> Optional[Generator[Maneuver, Maneuver, Maneuver]]:
    self.element = pilot.browser.get_existing("//a/*[text()='More information...']")

class TScraper(Raspador):
  def scrape(self):
    pilot = TPilot(browser=self.browser, user=self.user)
    maneuver = TNavigationManeuver()
    self.fly(pilot=pilot, maneuver=maneuver)
    super().scrape()

@pytest.fixture
def scraper():
  yield TScraper()

def test_scrape(scraper):
  scraper.scrape()