import pytest
import re

from ..parser import Parser

class TParser(Parser):
  def parse(self):
    element = self.soup.findAll(text=re.compile(r'Span two'))[0]
    from ..user_interactor import UserInteractor
    UserInteractor.shell(locals={'element': element, 'soup': self.soup, 'parser': self})

@pytest.fixture
def parser():
  with open('raspador/test/sample/sample-url.txt', 'r') as sample_url_file:
    sample_url = sample_url_file.read()
  with open('raspador/test/sample/sample.html', 'r') as sample_html_file:
    sample_html = sample_html_file.read()
  parser = TParser(source=sample_html, url=sample_url)
  yield parser

def test_find_text(parser):
  parser.parse()
