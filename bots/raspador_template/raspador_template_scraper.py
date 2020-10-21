import os

from pathlib import Path
from raspador import Raspador, ScriptManeuver
from typing import Dict
from .raspador_template_pilot import RaspadorTemplatePilot

class RaspadorTemplateBot(Raspador):
  def scrape(self):
    maneuver = ScriptManeuver(script_path=str(Path(__file__).parent / 'raspador_template_maneuver.py'))
    pilot = RaspadorTemplatePilot(config=self.configuration, browser=self.browser, user=self.user)
    self.fly(pilot=pilot, maneuver=maneuver)

    super().scrape()