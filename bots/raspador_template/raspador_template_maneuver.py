import re
import datetime
import importlib
import glob
import shutil

from pathlib import Path
from raspador_template.raspador_template_pilot import RaspadorTemplatePilot
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from raspador import Maneuver, OrdnanceManeuver, NavigationManeuver, SequenceManeuver, UploadReportRaspador, ClickXPathSequenceManeuver, InteractManeuver, OrdnanceParser, XPath, RaspadorNoOrdnanceError, ClickXPathManeuver, SeekParser, SoupElementParser, FindElementManeuver, ClickSoupElementManeuver, Element, ElementManeuver, ClickElementManeuver
from typing import Generator, Optional, Dict, List, Callable
from time import sleep
from bs4 import BeautifulSoup, Tag

class SignInManeuver(Maneuver[RaspadorTemplatePilot]):
  def attempt(self, pilot: RaspadorTemplatePilot):
    iframe = pilot.browser.driver.find_elements_by_tag_name('iframe')[0]
    pilot.browser.driver.switch_to_frame(iframe)

    email_element = yield ClickElementManeuver(
      instruction='click the email field',
      seeker=lambda p: p.soup.find('input', {'name': 'email'})
    )
    email_element.ordnance.send_keys(pilot.email)
    sleep(1)
    email_element.ordnance.send_keys(Keys.RETURN)
    sleep(1)

    password_element = yield ClickElementManeuver(
      instruction='click the password field',
      seeker=lambda p: p.soup.find('input', {'name': 'password'})
    )
    password_element.ordnance.send_keys(pilot.password)
    sleep(1)
    password_element.ordnance.send_keys(Keys.RETURN)
    pilot.browser.driver.switch_to.default_content()
    sleep(pilot.sign_in_wait)

class ClickNavigationLinkItemManeuver(Maneuver[RaspadorTemplatePilot]):
  item_text: str
  wait_after: int

  def __init__(self, item_text: str, wait_after: int):
    super().__init__()
    self.item_text = item_text
    self.wait_after = wait_after

  def attempt(self, pilot: RaspadorTemplatePilot, fly: Callable[[Maneuver], Maneuver]):
    click_manuever = ClickElementManeuver(
      instruction='click the Start button',
      seeker=lambda p: p.soup.find('a', text=self.item_text)
    )
    fly(click_manuever)
    sleep(self.wait_after)

class RaspadorTemplateManeuver(Maneuver[RaspadorTemplatePilot]):
  def attempt(self, pilot: RaspadorTemplatePilot):
    yield NavigationManeuver(url=f'file://{Path.cwd() / "bots" / "raspador_template" / "html" / "main.html"}')
    sleep(5)

    yield SignInManeuver()
    yield ClickNavigationLinkItemManeuver(item_text='Go', wait_after=1)

if __name__ == '__main__':
  enqueue_maneuver(RaspadorTemplateManeuver())
else:
  enqueue_maneuver(ClickNavigationLinkItemManeuver(item_text='Go', wait_after=1))