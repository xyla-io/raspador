from typing import Optional, List

class RaspadorError(Exception):
  pass

class RaspadorInputTimeoutError(RaspadorError):
  pass

class RaspadorDidNotCompleteManuallyError(RaspadorError):
  def __init__(self, maneuver: any):
    super().__init__(maneuver.name)

class RaspadorCannotInteractError(RaspadorError):
  pass

class RaspadorManeuverRequiredError(RaspadorError):
  def __init__(self, maneuver: any):
    super().__init__(f'{maneuver.name}: {maneuver.status.value}')

class RaspadorInvalidManeuverError(RaspadorError):
  def __init__(self, maneuver: any):
    super().__init__(f'Invalid maneuver: {maneuver}')

class RaspadorInvalidPositionError(RaspadorError):
  def __init__(self, position: any, maneuver: any, error: Optional[Exception]):
    super().__init__(f'Invalid position: {position} for maneuver: {maneuver}{f" with underlying error: {error}" if error else ""}')

class RaspadorSkip(RaspadorError):
  def __init__(self, maneuver: any):
    super().__init__(maneuver.name)

class RaspadorInteract(RaspadorError):
  def __init__(self, maneuver: any):
    super().__init__(maneuver.name)

class RaspadorSkipOver(RaspadorSkip):
  pass

class RaspadorSkipUp(RaspadorSkip):
  pass

class RaspadorSkipToBreak(RaspadorSkip):
  pass

class RaspadorQuit(RaspadorSkip):
  pass

class RaspadorNoOrdnanceError(RaspadorError):
  pass

class RaspadorElementError(RaspadorError):
  def __init__(self, element: any, method: str, error: Exception):
    super().__init__(f'{element.xpath} {method}(): {error}')

class RaspadorUnexpectedResultsError(RaspadorError):
  def __init__(self, unexpected_results: List[str]):
    super().__init__(f'Unexpected maneuver results: {", ".join(sorted(unexpected_results))}')

class RaspadorBotError(RaspadorError):
  def __init__(self, bot: 'Raspador', bot_error: str):
    super().__init__(f'Bot scrape failed for {bot.name} with error {bot_error}')
