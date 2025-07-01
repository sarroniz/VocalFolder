from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import pandas as pd

class ColumnStatsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.layout = QVBoxLayout(self)
        
        self.stats_table = QTableWidget()
        self.canvas = FigureCanvas(Figure(figsize=(4, 2)))

        self.layout.addWidget(QLabel("Descriptive Statistics"))
        self.layout.addWidget(self.stats_table)
        self.layout.addWidget(QLabel("Distribution"))
        self.layout.addWidget(self.canvas)

    def update_stats(self, data: pd.DataFrame, column_name: str):
        # clear if invalid or meta‐column
        if column_name in ["File", "Interval"] or column_name not in data.columns:
            self.stats_table.clearContents()
            self.stats_table.setRowCount(0)
            self.canvas.figure.clear()
            return

        series = data[column_name]

        # Try numeric conversion
        numeric = pd.to_numeric(series, errors="coerce").dropna()
        is_numeric = len(numeric) > 0

        self.stats_table.clearContents()
        self.canvas.figure.clear()

        if is_numeric:
            # ——— Numeric summary ———
            stats = {
                "Mean": numeric.mean(),
                "Median": numeric.median(),
                "SD": numeric.std(),
                "Min": numeric.min(),
                "Max": numeric.max()
            }

            # Build stats table
            self.stats_table.setRowCount(len(stats))
            self.stats_table.setColumnCount(2)
            self.stats_table.setHorizontalHeaderLabels(["Statistic", "Value"])
            for i, (name, val) in enumerate(stats.items()):
                self.stats_table.setItem(i, 0, QTableWidgetItem(name))
                self.stats_table.setItem(i, 1, QTableWidgetItem(f"{val:.2f}"))

            # Draw histogram
            ax = self.canvas.figure.add_subplot(111)
            ax.hist(numeric, bins=15)
            ax.set_title(f"Histogram of {column_name}")

        else:
            # ——— Nominal summary ———
            counts = series.fillna("<NA>").astype(str).value_counts()
            total  = len(series)

            # Build stats table: Category / Count / Percent
            self.stats_table.setRowCount(len(counts))
            self.stats_table.setColumnCount(3)
            self.stats_table.setHorizontalHeaderLabels(["Category", "Count", "% of Total"])
            for i, (cat, cnt) in enumerate(counts.items()):
                pct = cnt / total * 100
                self.stats_table.setItem(i, 0, QTableWidgetItem(cat))
                self.stats_table.setItem(i, 1, QTableWidgetItem(str(cnt)))
                self.stats_table.setItem(i, 2, QTableWidgetItem(f"{pct:.1f}%"))

            # Draw bar chart with explicit tick locations
            self.canvas.figure.clear()
            ax = self.canvas.figure.add_subplot(111)
            x = np.arange(len(counts))
            ax.bar(x, counts.values)
            ax.set_title(f"Distribution of {column_name}")
            ax.set_ylabel("Count")
            ax.set_xticks(x)
            ax.set_xticklabels(counts.index, rotation=45, ha="right")

        self.stats_table.resizeColumnsToContents()
        self.canvas.draw()