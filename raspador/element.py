from __future__ import annotations
from typing import Optional
from .base import XPath, BrowserElement
from .error import RaspadorElementError
from .browser_interactor import BrowserInteractor
from .parser import Parser, SeekParser
from bs4 import PageElement

def handle_element_error(f):
  def wrapper(*args, **kwargs):
    try:
      return f(*args, **kwargs)
    except (KeyboardInterrupt, RaspadorElementError) as e:
      raise
    except Exception as e:
      raise RaspadorElementError(element=args[0], method=f.__name__, error=e)
  return wrapper

class Element:
  highlight_enabled: bool=True

  xpath: XPath
  element: Optional[BrowserElement]
  soup_element: Optional[PageElement]
  browser: Optional[BrowserInteractor]
  parser: Parser
  timeout: float

  def __init__(self, xpath: Optional[XPath]=None, parent_xpath: Optional[XPath]=None, parent: Optional[Element]=None, element: Optional[BrowserElement]=None, soup_element: Optional[PageElement]=None, browser: Optional[BrowserInteractor]=None, parser: Optional[Parser]=None, timeout: float=5.0):
    if parent is not None:
      if parent_xpath is None:
        parent_xpath = parent.xpath
      if parser is None:
        parser = parent.parser
      if browser is None:
        browser = parent.browser
    self.parser = parser if parser is not None else Parser('')
    self.soup_element = soup_element
    if xpath is None:
      if self.soup_element is not None:
        xpath = self.parser.xpath_for_element(element=self.soup_element)
    self.xpath = f'{parent_xpath}/{xpath}' if parent_xpath is not None else xpath
    self.element = element
    self.browser = browser
    self.timeout = timeout

  @property
  @handle_element_error
  def element_source(self) -> str:
    if self.element is None:
      self.load_existing()
    return self.element.get_attribute('innerHTML')

  @property
  @handle_element_error
  def soup_source(self) -> str:
    return self.soup_element.content

  @property
  @handle_element_error
  def source(self) -> str:
    if self.element is None and self.soup_element is not None:
      return self.soup_source
    else:
      return self.element_source

  @handle_element_error
  def load_existing(self, timeout: Optional[float]=None) -> Element:
    timeout = timeout if timeout is not None else self.timeout if self.timeout is not None else 5.0
    self.element = self.browser.get_existing(xpath=self.xpath, timeout=timeout)
    return self

  @handle_element_error
  def load_visible(self, timeout: Optional[float]=None) -> Element:
    timeout = timeout if timeout is not None else self.timeout if self.timeout is not None else 5.0
    self.element = self.browser.get_visible(xpath=self.xpath, timeout=timeout)
    return self

  @handle_element_error
  def load_clickable(self, timeout: Optional[float]=None) -> Element:
    timeout = timeout if timeout is not None else self.timeout if self.timeout is not None else 5.0
    self.element = self.browser.get_clickable(xpath=self.xpath, timeout=timeout)
    return self

  @handle_element_error
  def expire(self) -> Element:
    self.element = None
    return self

  @handle_element_error
  def click(self):
    if self.element is None:
      self.load_clickable()
    self.element.click()
    return self

  @handle_element_error
  def send_keys(self, *value):
    if self.element is None:
      self.load_existing()
    self.element.send_keys(*value)
    return self

  @handle_element_error
  def add_class(self, value):
    if self.element is None:
      self.load_existing()
    self.browser.execute_script(f"arguments[0].classList.add('{value}')", self.element)
    return self

  @handle_element_error
  def remove_class(self, value):
    if self.element is None:
      self.load_existing()
    self.browser.execute_script(f"arguments[0].classList.remove('{value}')", self.element)
    return self

  @handle_element_error
  def highlight(self):
    if not self.highlight_enabled:
      return
    if self.element is None:
      self.load_existing()
    self.browser.execute_script(f"arguments[0].style.background = '{self.browser.next_color()}'", self.element)
  
  @handle_element_error
  def set_css_property(self, prop, value):
    if self.element is None:
      self.load_existing()
    self.browser.execute_script(f'arguments[0].style.{prop} = "{value}"', self.element)

  @handle_element_error
  def get_inline_css(self):
    """Returns a dictionary representation of the contents of an element's 'style' atrribute.
    """
    if self.element is None:
      self.load_existing()
    css_entries = [x for x in self.soup_element['style'].split(';') if x is not '']
    css_rules = dict([[value.strip() for value in entry.split(':')] for entry in css_entries])
    return css_rules

class ElementParser(SeekParser[Element]):
  pass
