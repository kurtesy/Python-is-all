import re
import mechanize

br = mechanize.Browser()
br.open("https://www.web.com/")
# follow second link with element text matching regular expression
