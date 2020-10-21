import uuid
from enum import Enum
from .style import Styled, CustomStyled, Format
from typing import Generic, TypeVar, Optional, List
from .error import RaspadorNoOrdnanceError

class UUID:
  id: str
  
  def __init__(self):
    self.id = uuid.uuid4().hex

  def __repr__(self) -> str:
    return self.id

class MenuOption(Enum):
  @property
  def option_text(self) -> str:
    raise NotImplementedError()

  @property
  def styled(self) -> Styled:
    return CustomStyled(text=self.option_text)

class ControlMode(MenuOption):
  automatic = 'a'
  manual = 'm'
  step_next = 'n'
  step_over = 'o'
  step_up = 'u'
  step_break = 'b'

  @property
  def option_text(self) -> str:
    if self is ControlMode.automatic:
      return '(A)utomatic'
    elif self is ControlMode.manual:
      return '(M)anual'
    elif self is ControlMode.step_next:
      return 'Step (N)ext'
    elif self is ControlMode.step_over:
      return 'Step (O)ver'
    elif self is ControlMode.step_up:
      return 'Step (U)p'
    elif self is ControlMode.step_break:
      return 'Step to (B)reakpoint'

  @property
  def styled(self) -> Styled:
    return CustomStyled(text=self.option_text, style=Format().green())

class ControlAction(MenuOption):
  skip_over = 'so'
  skip_up = 'su'
  skip_break = 'sb'
  done = 'c'
  repair_environment = 'e'
  quit = 'q'

  @property
  def option_text(self) -> str:
    if self is ControlAction.skip_over:
      return '(S)kip (O)ver'
    elif self is ControlAction.skip_up:
      return '(S)kip (U)p'
    if self is ControlAction.skip_break:
      return '(S)kip to (B)reakpoint'
    elif self is ControlAction.done:
      return 'Assume it is done and (C)ontinue'
    elif self is ControlAction.repair_environment:
      return 'Repair (E)nvironment to retry'
    elif self is ControlAction.quit:
      return '(Q)uit'

  @property
  def styled(self) -> Styled:
    return CustomStyled(text=self.option_text, style=Format().yellow())

O = TypeVar(any)
class Ordnance(Generic[O]):
  ordnance: Optional[O]=None
  no_ordnance_values: List[any]=[None]

  def load(self, ordnance: Optional[O]):
    self.ordnance = ordnance

  def deploy(self) -> Optional[O]:
    try:
      if self.no_ordnance_values and self.ordnance in self.no_ordnance_values:
        raise RaspadorNoOrdnanceError()
    except ValueError:
      pass
    ordnance = self.ordnance
    self.ordnance = None
    return ordnance

class OptionalOrdnance(Generic[O], Ordnance[O]):
  no_ordnance_values: List[any]=[]

XPath = str
BrowserElement = any
