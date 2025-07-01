from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QPoint

def get_unique_values_for_column(table, col):
    """Get unique values from a column"""
    unique_values = set()
    for row in range(table.rowCount()):
        item = table.item(row, col)
        if item and item.text().strip():
            unique_values.add(item.text().strip())
    return unique_values

def create_filter_menu(parent, col, unique_values, active_filters, callback):
    """Build and return a filter QMenu"""
    try:
        menu = QMenu(parent)

        # Select All
        act_all = QAction("Select All", parent)
        act_all.triggered.connect(lambda _, c=col, vals=unique_values: callback("select_all", c, vals))
        menu.addAction(act_all)

        # Clear All
        act_none = QAction("Clear All", parent)
        act_none.triggered.connect(lambda _, c=col: callback("clear_all", c))
        menu.addAction(act_none)

        menu.addSeparator()

        # Individual options
        for val in sorted(unique_values):
            a = QAction(val, parent)
            a.setCheckable(True)
            a.setChecked(val in active_filters.get(col, unique_values))
            a.toggled.connect(lambda checked, c=col, v=val: callback("toggle", c, v, checked))
            menu.addAction(a)

        return menu
    except Exception as e:
        print(f"❌ Error creating filter menu: {e}")
        return None

def show_menu_near_column(table, menu, col):
    """Show a menu near the column header"""
    try:
        header = table.horizontalHeader()
        section_pos = header.sectionViewportPosition(col)
        global_pos = table.mapToGlobal(header.pos()) + QPoint(section_pos, header.height())
        menu.exec(global_pos)
    except Exception as e:
        print(f"❌ Error showing filter menu: {e}")