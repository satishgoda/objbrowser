
""" 
   Program that shows the local Python environment using the inspect module
"""
from __future__ import print_function

import sys, argparse, os, logging, types, inspect

from PySide import QtCore, QtGui

logger = logging.getLogger(__name__)

DEBUGGING = True

PROGRAM_NAME = 'pyviewer'
PROGRAM_VERSION = '0.0.1'
PROGRAM_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
IMAGE_DIRECTORY = PROGRAM_DIRECTORY + '/images/'
ABOUT_MESSAGE = u"""%(prog)s version %(version)s
""" % {"prog": PROGRAM_NAME, "version": PROGRAM_VERSION}


        
def class_name(obj):
    """ Returns the name of the class of the object.
        Returns empty string if it cannot be determined, 
        e.g. in old-style classes.
    """
    try:
        return obj.__class__.__name__
    except AttributeError:
        return ''



class ColumnSettings(object):
    """ Class that stores INITIAL column settings. """
    
    def __init__(self, name, width=150, visible=True):
        """ Constructor to set mandatory and default settings) """
        self.name = name
        self.visible = visible
        self.width = width
        self.toggle_action = None  # action to show/hide column
        self.toggle_function = None # function that shows/hides column
        
        
# The main window inherits from a Qt class, therefore it has many 
# ancestors public methods and attributes.
# pylint: disable=R0901, R0902, R0904 

class ObjectBrowser(QtGui.QMainWindow):
    """ The main application.
    """
    # Tree column indices
    COL_NAME = 0
    COL_VALUE = 1
    COL_TYPE = 2
    COL_CLASS = 3
    
    def __init__(self, obj = None):
        """ Constructor
            :param obj: any python object or variable
        """
        super(ObjectBrowser, self).__init__()
        
        # Table columns
        self.col_settings = dict()
        self.col_settings[self.COL_NAME]  = ColumnSettings('Name')
        self.col_settings[self.COL_VALUE] = ColumnSettings('Value', width=300)
        self.col_settings[self.COL_TYPE]  = ColumnSettings('Type', visible=False)
        self.col_settings[self.COL_CLASS] = ColumnSettings('Class')
        
        # Views
        self._setup_actions()
        self._setup_menu()
        self._setup_views()
        self.setWindowTitle(PROGRAM_NAME)
        
        # Update views with model
        for settings in self.col_settings.itervalues():
            settings.toggle_action.setChecked(settings.visible)
        
        self._populate_tree(obj)


    def _setup_actions(self):
        """ Creates the MainWindow actions.
        """
        # Create actions for the table columns from its settings.
        for col_idx, settings in sorted(self.col_settings.iteritems()):
            settings.toggle_action = QtGui.QAction("Show {} Column".format(settings.name), 
                                                   self, checkable=True, checked=True,
                                                   statusTip = "Shows or hides the {} column".
                                                                format(settings.name))
            if col_idx >= 0 and col_idx <= 9:
                settings.toggle_action.setShortcut("Ctrl+{:d}".format(col_idx))
            settings.toggle_function = self._make_show_column_function(col_idx) # keep reference
            assert settings.toggle_action.toggled.connect(settings.toggle_function)

                              
    def _setup_menu(self):
        """ Sets up the main menu.
        """
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("C&lose", self.close_window, "Ctrl+W")
        file_menu.addAction("E&xit", self.quit_application, "Ctrl+Q")
        if DEBUGGING is True:
            file_menu.addSeparator()
            file_menu.addAction("&Test", self.my_test, "Ctrl+T")
        
        view_menu = self.menuBar().addMenu("&View")
        for _idx, settings in sorted(self.col_settings.iteritems()):
            view_menu.addAction(settings.toggle_action)
        
        self.menuBar().addSeparator()
        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction('&About', self.about)


    def _setup_views(self):
        """ Creates the UI widgets. 
        """
        central_splitter = QtGui.QSplitter(self, orientation = QtCore.Qt.Vertical)
        self.setCentralWidget(central_splitter)
        central_layout = QtGui.QHBoxLayout()
        central_splitter.setLayout(central_layout)
        
        # Tree widget
        self.obj_tree = QtGui.QTreeWidget()
        self.obj_tree.setColumnCount(len(self.col_settings))
        
        for idx, settings in self.col_settings.iteritems():
            self.obj_tree.headerItem().setText(idx, settings.name)  
            self.obj_tree.header().resizeSection(idx, settings.width)
        
        # Don't stretch last column, it doesn't play nice when columns are 
        # hidden and then shown again
        self.obj_tree.header().setStretchLastSection(False) 
        central_layout.addWidget(self.obj_tree)

        # Editor widget
        font = QtGui.QFont()
        font.setFamily('Courier')
        font.setFixedPitch(True)
        font.setPointSize(14)

        self.editor = QtGui.QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setFont(font)
        self.editor.setWordWrapMode(QtGui.QTextOption.NoWrap)
        central_layout.addWidget(self.editor)
        
        # Splitter parameters
        central_splitter.setCollapsible(0, False)
        central_splitter.setCollapsible(1, True)
        central_splitter.setSizes([400, 200])
        central_splitter.setStretchFactor(0, 0)
        central_splitter.setStretchFactor(1, 70)
               
        # Connect signals
        assert self.obj_tree.currentItemChanged.connect(self._update_details)


    # End of setup_methods
    # pylint: enable=W0201

    def my_test(self):
        """ Function for testing """
        logger.debug("my_test")
        
    
    def _populate_tree(self, obj):
        """ Fills the tree using a python object.
        """
        logger.debug("_populate_tree with object id = 0x{:x}".format(id(obj)))
        obj_type = type(obj)
        parent_item = self.obj_tree
        
        if obj_type == types.DictionaryType:
            for key, value in sorted(obj.iteritems()):
                tree_item = QtGui.QTreeWidgetItem(parent_item)                
                logger.debug("Inserting: {}".format(key))
                tree_item.setText(self.COL_NAME, key)
                tree_item.setText(self.COL_VALUE, repr(value))
                tree_item.setText(self.COL_TYPE, str(type(value)))
                tree_item.setText(self.COL_CLASS, class_name(value))
        else:
            logger.warn("Unexpected object type: {}".format(obj_type))
            
        #self.obj_tree.expandToDepth(1)

        
 
    @QtCore.Slot(QtGui.QTreeWidgetItem, QtGui.QTreeWidgetItem)
    def _update_details(self, current_item, _previous_item):
        """ Shows the object details in the editor
        """
        #self.editor.clear()
        self.editor.setPlainText(current_item.text(self.COL_VALUE))

    
    def _make_show_column_function(self, column_idx):
        """ Creates a function that shows or hides a column."""
        show_column = lambda checked: self.obj_tree.setColumnHidden(column_idx, not checked)
        return show_column     


    def about(self):
        """ Shows the about message window. """
        QtGui.QMessageBox.about(self, "About %s" % PROGRAM_NAME, ABOUT_MESSAGE)

    def close_window(self):
        """ Closes the window """
        self.close()
        
    def quit_application(self):
        """ Closes all windows """
        app = QtGui.QApplication.instance()
        app.closeAllWindows()

# pylint: enable=R0901, R0902, R0904        


def call_viewer_test():
    """ Test procedure. 
    """
    class OldStyleClass: pass
    class NewStyleClass(object): pass
    
    x_plus_2 = lambda x: x+2
    
    d = {'4': 44, 's': 11}
    a = 6
    b = 'seven'
    n = None
    lst = [4, '4', d, ['r', dir]]
    
    obj_browser = ObjectBrowser(obj = locals())
    obj_browser.resize(1000, 600)
    obj_browser.show()
    
    return obj_browser # to keep a reference

        
def main():
    """ Main program to test stand alone 
    """
    app = QtGui.QApplication(sys.argv)
    
    parser = argparse.ArgumentParser(description='Python abstract syntax tree viewer')
    parser.add_argument(dest='file_name', help='Python input file', nargs='?')
    parser.add_argument('-l', '--log-level', dest='log_level', default = 'debug', 
        help = "Log level. Only log messages with a level higher or equal than this "
            "will be printed. Default: 'debug'",
        choices = ('debug', 'info', 'warn', 'error', 'critical'))
    
    args = parser.parse_args()

    logging.basicConfig(level = args.log_level.upper(), 
        format='%(filename)20s:%(lineno)-4d : %(levelname)-7s: %(message)s')

    logger.info('Started {}'.format(PROGRAM_NAME))
    _obj_browser = call_viewer_test() # to keep a reference
    exit_code = app.exec_()
    logging.info('Done {}'.format(PROGRAM_NAME))
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
