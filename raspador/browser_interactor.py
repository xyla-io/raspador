import os
import zipfile

from .base import XPath, BrowserElement

from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Tuple
from enum import Enum
from config import interactor_config, environment_config
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import NoSuchElementException, TimeoutException

class BrowserInteractor:
  driver: any # the web driver object
  colors = ['red', 'orange']
  display: Optional[any]

  @classmethod
  def create_driver(cls, platform=environment_config['platform'], profile_directory_path: Optional[str]=None, display_size: Optional[Tuple[int, int]]=(1024, 768)) -> any:
    if platform == 'docker':
      from pyvirtualdisplay.smartdisplay import SmartDisplay
      cls.display = SmartDisplay(visible=0, size=display_size)
      cls.display.start()
      firefox_profile = webdriver.FirefoxProfile()
      firefox_profile.set_preference('browser.download.folderList', 2)
      firefox_profile.set_preference('browser.download.manager.showWhenStarting', False)
      firefox_profile.set_preference('browser.download.dir', os.getcwd())
      firefox_profile.set_preference('browser.helperApps.neverAsk.saveToDisk', 'text/csv, application/zip')
      return webdriver.Firefox(firefox_profile=firefox_profile)
    else:
      cls._add_geckodriver_to_path()
      path = profile_directory_path if profile_directory_path else interactor_config['geckodriver_profile_path']
      firefox_profile = webdriver.FirefoxProfile(path)
      firefox_profile.set_preference('browser.download.folderList', 2)
      firefox_profile.set_preference('browser.download.manager.showWhenStarting', False)
      firefox_profile.set_preference('browser.download.dir', os.getcwd())
      firefox_profile.set_preference('browser.helperApps.neverAsk.saveToDisk', 'text/csv, application/zip')
      return webdriver.Firefox(firefox_profile)

  @classmethod
  def _add_geckodriver_to_path(cls):
    geckodriver_path = interactor_config['geckodriver_directory_path']
    if geckodriver_path in os.environ['PATH'].split(':'):
      return
    os.environ['PATH'] = '{}:{}'.format(os.environ['PATH'], geckodriver_path)

  def __init__(self, driver: Optional[any]=None, window_size: Optional[Tuple[int, int]]=(1024, 768)):
    self.driver = driver if driver is not None else type(self).create_driver()
    if window_size:
      self.driver.set_window_size(*window_size)

  def navigate(self, url: str):
    self.driver.get(url)
  
  def get(self, conditions: any, timeout: float=10.0) -> Optional[BrowserElement]:
    wait = WebDriverWait(self.driver, timeout)
    try:
      return wait.until(conditions)
    except TimeoutException:
      return None

  def get_existing(self, xpath: str, timeout: float = 10.0) -> Optional[BrowserElement]:
    return self.get(
      conditions=expected_conditions.presence_of_element_located((By.XPATH, xpath)),
      timeout=timeout
    )
  
  def get_visible(self, xpath: str, timeout: float = 10.0) -> Optional[BrowserElement]:
    return self.get(
      conditions=expected_conditions.visibility_of_element_located((By.XPATH, xpath)),
      timeout=timeout
    )

  def get_clickable(self, xpath: str, timeout: float = 10.0) -> Optional[BrowserElement]:
    return self.get(
      conditions=expected_conditions.element_to_be_clickable((By.XPATH, xpath)),
      timeout=timeout
    )

  def element_exists(self, xpath: str) -> bool:
    try:
      element = self.driver.find_element_by_xpath(xpath=xpath)
      return element is not None
    except NoSuchElementException:
      return False

  @property
  def current_url(self) -> str:
    return self.driver.current_url

  @property
  def current_source(self) -> str:
    return self.driver.page_source

  def execute_script(self, *args, **kwargs):
    return self.driver.execute_script(*args, **kwargs)

  def next_color(self) -> str:
    self.colors = self.colors[1:] + self.colors[:1]
    return self.colors[-1]

  def create_screenshot(self) -> Optional[any]:
    return self.display.waitgrab() if self.display else None

  def save_screenshot(self, path: str) -> bool:
    image = self.create_screenshot()
    if image is None:
      return False
    image.save(path)
    return True
