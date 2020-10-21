import pytest
import code
import functools
import subprocess

from typing import List
from ..user_interactor import Console, UserInteractor
from ..base import ControlMode

class TestDriver:
  current_url: str='http://example.com'
  page_source: str='<a href="http://example.com">link text</a>'

@pytest.fixture
def driver() -> any:
  yield TestDriver()

@pytest.fixture
def interactor(driver) -> UserInteractor:
  interactor = UserInteractor(driver=driver)
  yield interactor

def test_menu(interactor, driver):
  interactor.present_menu(options=list(ControlMode), default_option=ControlMode.automatic)

def test_html_viewing():
  html = '<a href="http://example.com">link text</a>'
  with open('output/html/test.html', 'w') as f:
    f.write(html)
  subprocess.call(['w3m', 'output/html/test.html'])

def test_recorder():
  console = Console(locals={})
  console.interact(banner='Type CTRL-D to exit.', exitmsg='Thank you.')
  print(console.record)
  assert console.record is not None

def test_recording():
  record = []

  def read_and_record(record: List[str]):
    def wrap(f):
      @functools.wraps(f)
      def wrapper(*args, **kwargs):
        result = f(*args, **kwargs)
        record.append(result)
        return result
      return wrapper
    return wrap

  @read_and_record(record=record)
  def readf(*args, **kwargs):
    return input(*args, **kwargs)

  code.interact(banner='Type CTRL-D to exit', readfunc=readf)

  print(record)
  assert record is not None
