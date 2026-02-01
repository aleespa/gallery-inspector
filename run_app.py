import sys
import tkinter
# Mock tix for Python 3.13+ compatibility with tkinterdnd2
if not hasattr(tkinter, 'tix'):
    class DummyTix:
        Tk = tkinter.Tk
    sys.modules['tkinter.tix'] = DummyTix
    tkinter.tix = DummyTix

from ui import GalleryInspectorUI

if __name__ == "__main__":
    app = GalleryInspectorUI()
    app.mainloop()
