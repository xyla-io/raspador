import pytest

from ..browser_interactor import BrowserInteractor

@pytest.fixture
def browser():
  browser = BrowserInteractor()
  yield browser

def test_browser(browser):
  """
  Test that the interactor can interact.
  """
  browser.navigate('https://example.com/')
  element = browser.get_existing("//a/*[text()='More information...']")
  assert element is not None
  import pdb; pdb.set_trace()
  