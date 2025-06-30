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
        select_all_action = QAction("Select All", parent)
        select_all_action.triggered.connect(lambda: callback("select_all", col, unique_values))
        menu.addAction(select_all_action)

        # Clear All
        clear_all_action = QAction("Clear All", parent)
        clear_all_action.triggered.connect(lambda: callback("clear_all", col, unique_values))
        menu.addAction(clear_all_action)

        menu.addSeparator()

        # Individual options
        for val in sorted(unique_values):
            action = QAction(val, parent)
            action.setCheckable(True)
            action.setChecked(val in active_filters.get(col, set()))
            action.toggled.connect(lambda checked, v=val: callback("toggle", col, v, checked))
            menu.addAction(action)

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