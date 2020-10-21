import os

from pathlib import Path
from raspador import Raspador, ScriptManeuver
from typing import Dict
from .map_graph_pilot import MapGraphPilot

class MapGraphBot(Raspador):
  def scrape(self):
    maneuver = ScriptManeuver(script_path=str(Path(__file__).parent / 'map_graph_maneuver.py'))
    pilot = MapGraphPilot(config=self.configuration, browser=self.browser, user=self.user)
    self.fly(pilot=pilot, maneuver=maneuver)

    super().scrape()