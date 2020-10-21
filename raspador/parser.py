from __future__ import annotations
from .base import Ordnance
from .browser_interactor import BrowserInteractor
from urllib.parse import urljoin
from typing import TypeVar, Generic, Optional, Callable, Dict, List
from bs4 import BeautifulSoup, PageElement
from io_map import IOMap

class Parser(IOMap):
  source: Optional[str]
  url: Optional[str]
  soup: Optional[BeautifulSoup]

  @classmethod
  def from_browser(cls, browser: BrowserInteractor):
    return cls(source=browser.current_source, url=browser.current_url)

  def __init__(self, source: Optional[str]=None, url: Optional[str]=None):
    self.url = url
    self.source = source
    self.load_soup()

  @property
  def name(self) -> str:
    return type(self).__name__

  @property
  def instruction(self) -> str:
    return f'parse {self.name}'

  def convert_url_to_absolute(self, url: str) -> str:
    if self.url is None: return url
    return urljoin(self.url, url)

  def load_soup(self) -> Optional[BeautifulSoup]:
    self.soup = BeautifulSoup(self.source, features='html.parser') if self.source is not None else None
    return self.soup

  def load_browser(self, browser: BrowserInteractor):
    self.source = browser.current_source
    self.url = browser.current_url
    self.load_soup()

  def parse(self, *args, **kwargs) -> Parser:
    return self

  def xpath_for_element(self, element: PageElement) -> str:
    xpath_components_reversed = []
    e = element
    while e.parent is not None:
      if e.name:
        index = 1
        for c in e.parent.children:
          if c is e:
            break
          if c.name != e.name:
            continue
          index += 1
        xpath_components_reversed.append(f'{e.name}[{index}]')
      e = e.parent
    return '/'.join(reversed(xpath_components_reversed))

  def run(self, *args, **kwargs):
    self.parse(*args, **kwargs)

O = TypeVar(any)
class OrdnanceParser(Generic[O], Parser, Ordnance[O]):
  def run(self, *args, **kwargs):
    super().run(*args, **kwargs)
    return self.ordnance

class SeekParser(Generic[O], OrdnanceParser[O]):
  _instruction: str
  seeker: Callable[[BeautifulSoup, SeekParser, ...], Optional[O]]

  def __init__(self, instruction: str, seeker: Optional[Callable[[BeautifulSoup, SeekParser, ...], Optional[PageElement]]]=None, source: Optional[str]=None, url: Optional[str]=None, seek: Dict[str, any]={}):
    self._instruction = instruction
    self.seeker = seeker if seeker is not None else SoupSeeker(**seek)
    super().__init__(source=source, url=url)

  @property
  def instruction(self) -> str:
    return self._instruction

  def parse(self, *args, **kwargs):
    self.ordnance = self.seeker(self, *args, **kwargs)
    return self

class SoupElementParser(SeekParser[PageElement]):
  pass

class Seeker(IOMap):
  def __call__(self, parser: SeekParser, *args, **kwargs) -> Optional[PageElement]:
    return None

class SoupSeeker(Seeker):
  soup_args: List[any]
  soup_kwargs: Dict[str, any]

  def __init__(self, *args, **kwargs):
    self.soup_args = args
    self.soup_kwargs = kwargs

  def __call__(self, parser: SeekParser, *args, **kwargs):
    page_element = parser.soup.find(*self.soup_args, **self.soup_kwargs)
    return page_element

class SoupIndexSeeker(SoupSeeker):
  target_index: int

  def __init__(self, target_index: int, *args, **kwargs):
    self.target_index = target_index
    super().__init__(*args, **kwargs)
    
  def __call__(self, parser: SeekParser, *args, **kwargs):
    page_elements = parser.soup.find(*self.soup_args, **self.soup_kwargs)
    try:
      page_element = page_elements[self.target_index]
    except IndexError:
      page_element = None
    return page_element
