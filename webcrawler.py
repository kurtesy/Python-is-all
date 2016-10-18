import spynner

browser = spynner.Browser()
browser.load("http://stackoverflow.com/q/3369073/")
browser.snapshot().save('file.png')
browser.close()
