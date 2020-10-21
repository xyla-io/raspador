from __future__ import annotations
from .base import MenuOption, ControlMode, ControlAction, UUID, Ordnance, XPath
from .error import RaspadorManeuverRequiredError, RaspadorInteract, RaspadorSkip, RaspadorDidNotCompleteManuallyError, RaspadorQuit
from .user_interactor import Interaction
from .pilot import Pilot
from .style import Format, Styled, CustomStyled
from .parser import SoupElementParser, OrdnanceParser, SeekParser
from typing import Optional, List, Generator, TypeVar, Generic, Union, Callable, Dict
from enum import Enum
from datetime import datetime
from time import sleep
from bs4 import BeautifulSoup, PageElement
from .element import Element
from io_map import IOMap
from pprint import pformat

class Position:
  id: UUID
  entry_time: Optional[datetime]=None
  stable_time: Optional[datetime]=None
  option: MenuOption
  error: Optional[Exception]

  def __init__(self, option: MenuOption, error: Optional[Exception]=None):
    self.id = UUID()
    self.option = option
    self.error = error

  @property
  def description(self) -> str:
    error_description = f' – {type(self.error).__name__}' if self.error else ''
    return f'{self.option.option_text}{error_description}'

  def enter(self) -> Position:
    assert self.entry_time is None
    self.entry_time = datetime.utcnow()
    return self

  def stabilize(self, error: Optional[Exception]=None) -> Position:
    assert self.entry_time is not None and self.stable_time is None
    self.error = error
    self.stable_time = datetime.utcnow()
    return self

P = TypeVar(Pilot)
class Maneuver(Generic[P], IOMap):
  class Status(Enum):
    ready = 'Ready'
    in_progress = 'In progress'
    holding = 'On hold'
    completed = 'Completed'
    error = 'Error'
    skipped = 'Skipped'

    @property
    def finished(self) -> bool:
      return self in [Maneuver.Status.completed, Maneuver.Status.skipped]

  id: UUID
  trajectory: List[Position]

  def __init__(self):
    self.id = UUID()
    self.trajectory = []

  @property
  def position(self) -> Optional[Position]:
    if not self.trajectory:
      return None
    return self.trajectory[-1]

  @property
  def status(self) -> Maneuver.Status:
    if self.position is None:
      return Maneuver.Status.ready
    elif self.position.stable_time is None:
      return Maneuver.Status.in_progress
    elif self.position.error:
      return Maneuver.Status.skipped if isinstance(self.position.error, RaspadorSkip) else Maneuver.Status.error
    elif isinstance(self.position.option, ControlMode) or self.position.option is ControlAction.done:
      return Maneuver.Status.completed
    else:
      return Maneuver.Status.holding
      
  class RepresentationKey(Enum):
    error = 'error'
    load = 'load'
    map = 'map'
    operation = 'operation'

    @property
    def name(self) -> str:
      return self.value.title()

  @property
  def instruction(self) -> str:
    try:
      return f'perform {self.name} {IOMap.__str__(self)}'
    except (SystemExit, KeyboardInterrupt):
      raise
    except Exception:
      return f'perform {self.name}'

  @property
  def detail(self) -> Union[Styled, List[any]]:
    return CustomStyled(text=self.instruction, style=Format().cyan())

  @property
  def name(self) -> str:
    return type(self).__name__

  @property
  def options(self) -> List[MenuOption]:
    return [
      *ControlMode,
      *Interaction,
      *[c for c in ControlAction if c is not ControlAction.repair_environment],
    ]

  @property
  def representation(self) -> Dict[str, any]:
    representation = {
      **({Maneuver.RepresentationKey.error.name: repr(self.position.error)} if self.position is not None and self.position.error is not None else {}),
      Maneuver.RepresentationKey.map.name: self.get_populated_map(depth=0),
      Maneuver.RepresentationKey.operation.name: self.instruction,
    }
    return representation

  def attempt(self, pilot: P, fly: Callable[[Maneuver], Maneuver], scraper: 'Raspador') -> Optional[Generator[Optional[Maneuver], Maneuver, Optional[Maneuver]]]:
    super().run(**self.populated_run)

  def require(self, maneuver: Maneuver) -> Maneuver:
    if maneuver.status is not Maneuver.Status.completed:
      raise RaspadorManeuverRequiredError(maneuver=maneuver)
    return maneuver

  def abort(self, error: Optional[Exception]):
    pass

  def attempt_manually(self, pilot: P, fly: Callable[[Maneuver], Maneuver]) -> Optional[Generator[Optional[Maneuver], Maneuver, Optional[Maneuver]]]:
    if not pilot.user.present_confirmation(prompt=f'Enter (Y)es when completed or (N)o to cancel', default_response=True):
      raise RaspadorDidNotCompleteManuallyError(maneuver=self)

  def run(self, **kwargs):
    fly: Callable[[Maneuver], Maneuver] = self['iocontext.fly']
    self.prepare_run(**kwargs)
    fly(self)
    self.clear_run()

  def __str__(self):
    try:
      representation = {**self.representation}
      components = {}
      for key in Maneuver.RepresentationKey:
        if key.name in representation:
          components[key.name] = representation[key.name]
          del representation[key.name]
      for name, value in representation.items():
        components[name] = value
      return f'{pformat(components, indent=2, width=80)} {self.__repr__()}'
    except (SystemExit, KeyboardInterrupt):
      raise
    except Exception:
      return super().__str__()

  def __repr__(self):
    return super().__repr__()

O = TypeVar(any)
class OrdnanceManeuver(Generic[P, O], Maneuver[P], Ordnance[O]):
  def attempt(self, pilot: P, fly: Callable[[Maneuver], Maneuver], scraper: 'Raspador') -> Optional[Generator[Optional[Maneuver], Maneuver, Optional[Maneuver]]]:
    self.load(IOMap.run(self, **self.populated_run))

  def run(self, **kwargs) -> O:
    super().run(**kwargs)
    return self.ordnance

  @property
  def representation(self) -> Dict[str, any]:
    return {
      **super().representation,
      **({Maneuver.RepresentationKey.load.name: self.ordnance} if self.ordnance is not None else {})
    }

class NavigationManeuver(Generic[P], Maneuver[P]):
  url: str

  def __init__(self, url:str):
    self.url = url
    super().__init__()

  @property
  def instruction(self) -> str:
    return f'navigate to {self.url}'

  def attempt(self, pilot: P):
    pilot.browser.navigate(url=self.url)

class ClickXPathManeuver(Generic[P], OrdnanceManeuver[P, Element]):
  xpath: XPath

  def __init__(self, xpath: XPath):
    self.xpath = xpath
    super().__init__()

  @property
  def instruction(self) -> str:
    return f'click element at xpath {self.xpath}'

  def attempt(self, pilot: P) -> Optional[Generator[Optional[Maneuver], Maneuver, Optional[Maneuver]]]:
    element = Element(xpath=self.xpath, browser=pilot.browser)
    element.highlight()
    element.click()
    self.ordnance = element
  
class SequenceManeuver(Generic[P], Maneuver[P]):
  index: int = 0
  sequence: List[Maneuver]
  pause_interval: float

  def __init__(self, sequence: List[Maneuver]=[], pause_interval: float=0):
    self.sequence = [*sequence]
    self.pause_interval = pause_interval
    super().__init__()

  @property
  def instruction(self) -> str:
    return f'perform {self.name} {self.index}/{len(self.sequence)}'

  @property
  def detail(self) -> Union[Styled, List[any]]:
    return [m.detail for m in self.sequence]

  @property
  def empty(self) -> bool:
    return not self.sequence
  
  def append(self, maneuver: Maneuver):
    self.sequence.append(maneuver)

  def clear(self):
    self.sequence.clear()

  def maneuver_is_required(self, index: int, maneuver: Maneuver) -> bool:
    return True

  def attempt(self, pilot: P) -> Optional[Generator[Optional[Maneuver], Maneuver, Optional[Maneuver]]]:
    self.index = 0
    while self.index < len(self.sequence):
      maneuver = yield self.sequence[self.index]
      if self.maneuver_is_required(index=self.index, maneuver=maneuver):
        self.require(maneuver)
      self.index += 1
      sleep(self.pause_interval)

class ClickXPathSequenceManeuver(Generic[P], SequenceManeuver[P]):
  xpaths: List[XPath]

  def __init__(self, xpaths: List[XPath], pause_interval: float=2.0):
    self.xpaths = xpaths

    sequence = [ClickXPathManeuver(xpath=x) for x in xpaths]
    super().__init__(sequence=sequence, pause_interval=pause_interval)

class BreakManeuver(Generic[P], Maneuver[P]):
  maneuver: Maneuver

  def __init__(self, maneuver: Maneuver):
    self.maneuver = maneuver
    super().__init__()

  @property
  def instruction(self) -> str:
    return f'continue when ready after {self.maneuver.name} ({self.maneuver.instruction})'

  @property
  def options(self) -> List[MenuOption]:
    return [o for o in super().options if o is not ControlMode.step_next]

class InteractManeuver(Maneuver[Pilot]):
  def attempt(self, pilot: P) -> Optional[Generator[Optional[Maneuver], Maneuver, Optional[Maneuver]]]:
    if not pilot.user.interactive:
      return
    if pilot.user.retry is None or len([p for p in self.trajectory if p.error]) < pilot.user.retry:
      raise RaspadorInteract(maneuver=self)

class InteractQueueManeuver(SequenceManeuver[Pilot]):
  def maneuver_is_required(self, index: int, maneuver: Maneuver) -> bool:
    return False

class FindElementManeuver(OrdnanceManeuver[Pilot, PageElement]):
  parser: SoupElementParser

  def __init__(self, parser: SoupElementParser):
    self.parser = parser
    super().__init__()

  @property
  def instruction(self) -> str:
    return f'perform {self.name} [{self.parser.name}]'

  def attempt(self, pilot: P) -> Optional[Generator[Optional[Maneuver], Maneuver, Optional[Maneuver]]]:
    self.ordnance = self.parser.parse().deploy()

class ClickSoupElementManeuver(OrdnanceManeuver[Pilot, any]):
  parser: SoupElementParser
  xpath_prefix: str

  def __init__(self, parser: SoupElementParser, xpath_prefix: str='//'):
    self.parser = parser
    self.xpath_prefix = xpath_prefix
    super().__init__()

  @property
  def instruction(self) -> str:
    return f'perform {self.name} [{self.parser.name}]'

  def attempt(self, pilot: P) -> Optional[Generator[Optional[Maneuver], Maneuver, Optional[Maneuver]]]:
    find = yield FindElementManeuver(parser=self.parser)
    xpath = f'{self.xpath_prefix}{find.parser.xpath_for_element(element=find.deploy())}'
    yield ClickXPathManeuver(xpath=xpath)

class ParseOrdnanceManeuver(Generic[P, O], OrdnanceManeuver[P, O]):
  parser: OrdnanceParser[O]

  def __init__(self, parser: OrdnanceParser[O]):
    self.parser = parser
    super().__init__()

  @property
  def name(self) -> str:
    return f'{super().name}>{self.parser.name}'

  @property
  def instruction(self) -> str:
    return self.parser.instruction

  def attempt(self, pilot: P) -> Optional[Generator[Optional[Maneuver], Maneuver, Optional[Maneuver]]]:
    self.ordnance = self.parser.parse().deploy()

class SeekManeuver(Generic[P, O], ParseOrdnanceManeuver[P, O]):
  parser: SeekParser[O]

  def __init__(self, instruction: str, seeker: Callable[[BeautifulSoup, SeekParser, ...], O], source: Optional[str]=None, url: Optional[str]=None, seek: Dict[str, any]={}):
    parser = SeekParser(instruction=instruction, seeker=seeker, source=source, url=url, seek=seek)
    super().__init__(parser=parser)

  def attempt(self, pilot: P) -> Optional[Generator[Optional[Maneuver], Maneuver, Optional[Maneuver]]]:
    if self.parser.source is None:
      self.parser.source = pilot.browser.current_source
      self.parser.url = pilot.browser.current_url
      self.parser.load_soup()
      self.ordnance = self.parser.parse().deploy()
      self.parser.source = None
      self.parser.url = None
      self.parser.load_soup()
    else:
      self.ordnance = self.parser.parse().deploy()

class ScriptQueueManeuver(SequenceManeuver[Pilot]):
  pass

class ScriptManeuver(Maneuver[Pilot]):
  script_path: str
  confirm: bool

  def __init__(self, script_path: str, confirm: bool=False):
    self.script_path = script_path
    self.confirm = confirm
    super().__init__()

  def attempt(self, pilot: Pilot) -> Optional[Generator[Optional[Maneuver], Maneuver, Optional[Maneuver]]]:
    with open(self.script_path, 'r') as f:
      code = f.read()
    queue = ScriptQueueManeuver()
    def enqueue_maneuver(maneuver: Maneuver):
      queue.append(maneuver)
    user_locals = pilot.user.locals
    pilot.user.locals = {
      **user_locals,
      'maneuver_queue': queue,
      'enqueue_maneuver': enqueue_maneuver,
      '__name__': '__main__'
    }
    pilot.user.run_code(code=code, file_path=self.script_path, description=self.instruction, confirm=self.confirm)
    pilot.user.locals = user_locals
    if not queue.empty:
      queued = yield queue
      self.require(queued)

class ElementManeuver(Generic[P], OrdnanceManeuver[P, Element]):
  seek_maneuver: Optional[SeekManeuver[P, PageElement]]
  xpath: Optional[XPath]
  parent_xpath: Optional[XPath]
  parent: Optional[Element]
  element: Optional[Element]
  timeout: Optional[float]
  _instruction: str

  def __init__(self, instruction: str, seeker: Optional[Callable[[BeautifulSoup, SeekParser, ...], PageElement]]=None, source: Optional[str]=None, url: Optional[str]=None, xpath: Optional[XPath]=None, parent_xpath: Optional[XPath]=None, parent: Optional[Element]=None, timeout: Optional[float]=None, seek: Optional[Dict[str, any]]=None, element: Optional[Element]=None):
    self.seek_maneuver = SeekManeuver[P, PageElement](
      instruction=instruction, 
      seeker=seeker, 
      source=source, 
      url=url,
      seek=seek
    ) if seeker is not None or seek is not None else None
    self.xpath = xpath
    self.parent_xpath = parent_xpath
    self.parent = parent
    self.element = element
    self.timeout = timeout
    self._instruction = instruction
    super().__init__()

  @property
  def instruction(self) -> str:
    return f'perform {self.name} {self._instruction}'

  def attempt(self, pilot: P) -> Optional[Generator[Optional[Maneuver], Maneuver, Optional[Maneuver]]]:
    if self.element is not None:
      self.load(self.element)
      return
    soup_element = (yield self.seek_maneuver).deploy() if self.seek_maneuver else None
    self.ordnance = Element(
      xpath=self.xpath,
      parent_xpath=self.parent_xpath,
      parent=self.parent,
      soup_element=soup_element,
      browser=pilot.browser,
      parser=self.seek_maneuver.parser if self.seek_maneuver else None,
      timeout=self.timeout
    )

class ClickElementManeuver(Generic[P], ElementManeuver[P]):
  def attempt(self, pilot: P) -> Optional[Generator[Optional[Maneuver], Maneuver, Optional[Maneuver]]]:
    attempt = super().attempt(pilot=pilot)
    if attempt is not None:
      yield from attempt
    self.ordnance.click()

class QuitManeuver(Maneuver[Pilot]):
  def attempt(self, pilot: P) -> Optional[Generator[Optional[Maneuver], Maneuver, Optional[Maneuver]]]:
    raise RaspadorQuit(maneuver=self)

