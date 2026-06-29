# ==========================================================
# LLA ↔ DCA Converter
# Professional Tkinter Version (Dynamic Columns with Scrollable Sidebar)
# ==========================================================

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

import pandas as pd
import numpy as np

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from mpl_toolkits.mplot3d import Axes3D

try:
    import tkintermapview
    MAP_AVAILABLE = True
except ImportError:
    MAP_AVAILABLE = False

# ==========================================================
# WGS84 CONSTANTS
# ==========================================================

a = 6378137.0
f = 1 / 298.257223563
e2 = f * (2 - f)
b = a * (1 - f)
ep2 = (a**2 - b**2) / b**2


# ==========================================================
# LLA -> ECEF / ECEF -> LLA / ENU CONVERSIONS
# ==========================================================

def lla_to_ecef(lat_deg, lon_deg, h):
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    N = a / np.sqrt(1 - e2 * np.sin(lat)**2)
    x = (N + h) * np.cos(lat) * np.cos(lon)
    y = (N + h) * np.cos(lat) * np.sin(lon)
    z = (N * (1 - e2) + h) * np.sin(lat)
    return np.array([x, y, z])

def ecef_to_lla(x, y, z):
    p = np.sqrt(x**2 + y**2)
    theta = np.arctan2(z * a, p * b)
    lon = np.arctan2(y, x)
    lat = np.arctan2(z + ep2 * b * np.sin(theta)**3, p - e2 * a * np.cos(theta)**3)
    N = a / np.sqrt(1 - e2 * np.sin(lat)**2)
    h = p / np.cos(lat) - N
    return np.degrees(lat), np.degrees(lon), h

def ecef_to_enu(target_ecef, ref_lat, ref_lon, ref_h):
    ref_ecef = lla_to_ecef(ref_lat, ref_lon, ref_h)
    dx = target_ecef - ref_ecef
    lat = np.radians(ref_lat)
    lon = np.radians(ref_lon)

    R = np.array([
        [-np.sin(lon), np.cos(lon), 0],
        [-np.sin(lat)*np.cos(lon), -np.sin(lat)*np.sin(lon), np.cos(lat)],
        [np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)]
    ])
    enu = R @ dx
    return enu[0], enu[1], enu[2]

def enu_to_ecef(east, north, up, ref_lat, ref_lon, ref_h):
    lat = np.radians(ref_lat)
    lon = np.radians(ref_lon)
    ref_ecef = lla_to_ecef(ref_lat, ref_lon, ref_h)

    R = np.array([
        [-np.sin(lon), -np.sin(lat)*np.cos(lon), np.cos(lat)*np.cos(lon)],
        [np.cos(lon), -np.sin(lat)*np.sin(lon), np.cos(lat)*np.sin(lon)],
        [0, np.cos(lat), np.sin(lat)]
    ])
    dxyz = R @ np.array([east, north, up])
    return ref_ecef + dxyz

def lla_to_dca(m_lat, m_lon, m_alt, l_lat, l_lon, l_alt, l_azimuth_deg):
    m_ecef = lla_to_ecef(m_lat, m_lon, m_alt)
    east, north, up = ecef_to_enu(m_ecef, l_lat, l_lon, l_alt)
    az = np.radians(l_azimuth_deg)
    down_range = east * np.sin(az) + north * np.cos(az)
    cross_range = east * np.cos(az) - north * np.sin(az)
    return down_range, cross_range, m_alt

def dca_to_lla(down_range, cross_range, altitude, l_lat, l_lon, l_alt, l_azimuth_deg):
    az = np.radians(l_azimuth_deg)
    east = down_range * np.sin(az) + cross_range * np.cos(az)
    north = down_range * np.cos(az) - cross_range * np.sin(az)
    up_guess = 0.0
    for _ in range(3):
        ecef_approx = enu_to_ecef(east, north, up_guess, l_lat, l_lon, l_alt)
        lat, lon, _ = ecef_to_lla(ecef_approx[0], ecef_approx[1], ecef_approx[2])
        target_ecef = lla_to_ecef(lat, lon, altitude)
        _, _, up_guess = ecef_to_enu(target_ecef, l_lat, l_lon, l_alt)    
    return lat, lon, altitude


# ==========================================================
# DATAFRAME TABLE CLASS
# ==========================================================

class DataFrameTable:
    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        self.tree = ttk.Treeview(self.frame, show="headings")
        self.vsb = ttk.Scrollbar(self.frame, orient="vertical", command=self.tree.yview)
        self.hsb = ttk.Scrollbar(self.frame, orient="horizontal", command=self.tree.xview)

        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")

        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

    def widget(self):
        return self.frame

    def clear(self):
        self.tree.delete(*self.tree.get_children())

    def load_dataframe(self, df):
        self.clear()
        columns = list(df.columns)
        self.tree["columns"] = columns

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, stretch=True, anchor="center")

        for _, row in df.iterrows():
            self.tree.insert("", "end", values=list(row))
        self.tree.update_idletasks()


# ==========================================================
# DARK THEME APPLICATION
# ==========================================================

def apply_dark_theme(root):
    style = ttk.Style()
    style.theme_use("clam")
    
    # Theme Palette Configuration
    BG_MAIN = "#0f172a"
    BG_SURFACE = "#1e293b"
    ACCENT = "#38bdf8"
    ACCENT_HOVER = "#0284c7"
    TEXT_MAIN = "#f8fafc"
    TEXT_MUTED = "#94a3b8"
    
    # NEW: Elegant Slate Gray-Blue for Hover/Active Highlight States
    BG_HOVER_HIGHLIGHT = "#334155" 
    
    FONT_FAMILY = "Segoe UI"

    style.configure(".", background=BG_MAIN, foreground=TEXT_MAIN, font=(FONT_FAMILY, 10))
    style.configure("TFrame", background=BG_MAIN)
    style.configure("TLabelframe", background=BG_SURFACE, foreground=ACCENT, borderwidth=1, relief="solid")
    style.configure("TLabelframe.Label", background=BG_SURFACE, foreground=ACCENT, font=(FONT_FAMILY, 10, "bold"))
    style.configure("TLabel", background=BG_SURFACE, foreground=TEXT_MAIN)
    
    # Buttons
    style.configure("TButton", background=ACCENT, foreground=BG_MAIN, font=(FONT_FAMILY, 10, "bold"), padding=(12, 6), borderwidth=0, relief="flat")
    style.map("TButton", background=[("active", ACCENT_HOVER), ("disabled", "#334155")], foreground=[("active", TEXT_MAIN), ("disabled", TEXT_MUTED)])
    
    # Data Tables (Treeview) Layout & Dynamic States
    style.configure("Treeview", background=BG_SURFACE, foreground=TEXT_MAIN, fieldbackground=BG_SURFACE, rowheight=30, font=(FONT_FAMILY, 10), borderwidth=0)
    style.map("Treeview", background=[("selected", ACCENT_HOVER)], foreground=[("selected", TEXT_MAIN)])
    
    # FIX: Explicit Table Heading Configuration & Hover Background Safeguard
    style.configure("Treeview.Heading", background="#111827", foreground=TEXT_MAIN, font=(FONT_FAMILY, 10, "bold"), padding=8, relief="flat")
    style.map("Treeview.Heading", 
              background=[("active", BG_HOVER_HIGHLIGHT), ("pressed", "#475569")],
              foreground=[("active", TEXT_MAIN)])

    # FIX: Explicit Conversion Mode Option (Radiobutton) Hover Layout
    style.configure("TRadiobutton", background=BG_SURFACE, foreground=TEXT_MAIN, font=(FONT_FAMILY, 10), padding=4)
    style.map("TRadiobutton", 
              background=[("active", BG_HOVER_HIGHLIGHT)],
              foreground=[("active", TEXT_MAIN)])
    
    # Notebook Tabs
    style.configure("TNotebook", background=BG_MAIN, borderwidth=0, tabmargins=[2, 4, 2, 0])
    style.configure("TNotebook.Tab", background="#111827", foreground=TEXT_MUTED, font=(FONT_FAMILY, 9, "bold"), padding=(14, 6))
    style.map("TNotebook.Tab", background=[("selected", BG_SURFACE)], foreground=[("selected", ACCENT)])

    # Dropdowns (Combobox)
    style.configure("TCombobox", fieldbackground="#1e293b", background="#0f172a", foreground="white", arrowcolor="white")
    style.map("TCombobox", fieldbackground=[("readonly", "#1e293b")], foreground=[("readonly", "white")])
    
    root.option_add("*TCombobox*Listbox.background", "#0f172a")
    root.option_add("*TCombobox*Listbox.foreground", "white")
    

# ==========================================================
# PLOT TAB MANAGER
# ==========================================================

class PlotTabs:

    LEGEND_ITEMS = [
        ("●", "#f59e0b", "Ground Station"),
        ("—", "#00bfff", "Trajectory"),
        ("●", "#22c55e", "Start Point"),
        ("●", "#ef4444", "End Point")
    ]

    def __init__(self, parent):
        self.main_frame = ttk.Frame(parent)
        self.current_df = None

        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill="both", expand=True)

        self.chart_tab = ttk.Frame(self.notebook)
        self.map_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.chart_tab, text="  Charts  ")
        self.notebook.add(self.map_tab, text="  Trajectory Map  ")

        self.left_frame = ttk.Frame(self.chart_tab)
        self.right_frame = ttk.Frame(self.chart_tab)
        self.left_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        self.control_frame = ttk.LabelFrame(self.left_frame, text="Custom Plot")
        self.control_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(self.control_frame, text="X Axis").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.x_var = tk.StringVar()
        self.x_combo = ttk.Combobox(self.control_frame, textvariable=self.x_var, state="readonly")
        self.x_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(self.control_frame, text="Y Axis").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.y_var = tk.StringVar()
        self.y_combo = ttk.Combobox(self.control_frame, textvariable=self.y_var, state="readonly")
        self.y_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.control_frame.columnconfigure(0, weight=1)
        self.control_frame.columnconfigure(1, weight=1)
        
        self.plot_button = ttk.Button(self.control_frame, text="Plot")
        self.plot_button.grid(row=2, column=0, padx=(5, 2), pady=10, sticky="e")
        
        self.save_button = ttk.Button(self.control_frame, text="Save Plot", command=self.save_plot_pdf)
        self.save_button.grid(row=2, column=1, padx=(2, 5), pady=10, sticky="w")

        self.fig2d = Figure(figsize=(6, 5))
        self.fig2d.patch.set_facecolor("#08121f")
        self.ax2d = self.fig2d.add_subplot(111)
        self.ax2d.set_facecolor("#08121f")
        self.canvas2d = FigureCanvasTkAgg(self.fig2d, self.left_frame)
        self.canvas2d.get_tk_widget().pack(fill="both", expand=True)

        self.fig3d = Figure(figsize=(6, 5))
        self.fig3d.patch.set_facecolor("#08121f")
        self.ax3d = self.fig3d.add_subplot(111, projection="3d")
        self.ax3d.set_facecolor("#08121f")
        self.canvas3d = FigureCanvasTkAgg(self.fig3d, self.right_frame)
        self.canvas3d.get_tk_widget().pack(fill="both", expand=True)

        self.map_widget = None

        if MAP_AVAILABLE:
            self.map_widget = tkintermapview.TkinterMapView(self.map_tab, corner_radius=0)
            self.map_widget.pack(fill="both", expand=True)
            self.map_widget.set_tile_server(
                "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png", max_zoom=19
            )
            self.map_widget.set_position(20.5, 85.5)
            self.map_widget.set_zoom(5)
            self._build_map_legend()
        else:
            ttk.Label(
                self.map_tab,
                text=(
                    "Trajectory Map requires the 'tkintermapview' package.\n\n"
                    "Install it with:  pip install tkintermapview\n"
                    "then restart the application."
                ),
                justify="center"
            ).pack(expand=True)

    def _build_map_legend(self):
        self.map_legend = tk.Frame(self.map_tab, bg="#0b1220", highlightthickness=1, highlightbackground="#334155")
        self.map_legend.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)

        tk.Label(self.map_legend, text="LEGEND", bg="#0b1220", fg="#7dd3fc",
                  font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(8, 4))

        for symbol, color, label in self.LEGEND_ITEMS:
            row = tk.Frame(self.map_legend, bg="#0b1220")
            row.pack(fill="x", padx=10, pady=1)
            tk.Label(row, text=symbol, bg="#0b1220", fg=color, font=("Segoe UI", 10, "bold")).pack(side="left")
            tk.Label(row, text=label, bg="#0b1220", fg="#cbd5e1", font=("Segoe UI", 8)).pack(side="left", padx=(6, 0))

        tk.Label(self.map_legend, text="Map: OpenStreetMap, CARTO", bg="#0b1220", fg="#475569",
                  font=("Segoe UI", 7)).pack(anchor="w", padx=10, pady=(6, 8))

    def widget(self):
        return self.main_frame

    def update_available_columns(self, df):
        self.current_df = df
        # Explicitly filter out 'launch_station' text from plot configurations
        cols = [col for col in df.columns if col != "launch_station"]
        self.x_combo["values"] = cols
        self.y_combo["values"] = cols
        if len(cols) >= 2:
            self.x_var.set(cols[0])
            self.y_var.set(cols[1])
        self.plot_button.configure(command=lambda: self.plot_custom(self.current_df))

    def plot_custom(self, df):
        if df is None or self.x_var.get() not in df.columns or self.y_var.get() not in df.columns:
            return
        x_col, y_col = self.x_var.get(), self.y_var.get()
        self.ax2d.clear()
        self.ax2d.set_facecolor("#08121f")
        self.ax2d.plot(df[x_col], df[y_col], color="#00bfff", linewidth=2.5)
        self.ax2d.set_title(f"{y_col} vs {x_col}", color="white")
        self.ax2d.set_xlabel(x_col, color="white")
        self.ax2d.set_ylabel(y_col, color="white")
        self.ax2d.tick_params(colors="white")
        self.ax2d.grid(color="#444444", linestyle="--", alpha=0.5)
        for spine in self.ax2d.spines.values():
            spine.set_color("white")
        self.canvas2d.draw()

    def save_plot_pdf(self):
        if self.current_df is None:
            messagebox.showwarning("Warning", "No active data found to generate a plot save.")
            return
            
        filename = filedialog.asksaveasfilename(
            title="Save Custom Plot as PDF", 
            defaultextension=".pdf", 
            filetypes=[("PDF Files", "*.pdf")]
        )
        if filename:
            try:
                self.fig2d.savefig(filename, format="pdf", facecolor=self.fig2d.get_facecolor(), edgecolor='none')
                messagebox.showinfo("Success", f"Plot exported safely to PDF structure:\n{filename}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def plot_3d(self, df, mode):
        if df is None:
            return
        self.ax3d.clear()
        self.ax3d.set_facecolor("#08121f")

        if mode == "LLA_TO_DCA":
            self.ax3d.plot(df["down_range_m"], df["cross_range_m"], df["altitude_m"], color="#00bfff", linewidth=2.5)
            self.ax3d.set_title("3D Trajectory (DR-CR-Altitude)", color="white")
            self.ax3d.set_xlabel("Down Range (m)", color="white")
            self.ax3d.set_ylabel("Cross Range (m)", color="white")
            self.ax3d.set_zlabel("Altitude (m)", color="white")
        else:
            self.ax3d.plot(df["lon_deg"], df["lat_deg"], df["alt_m"], color="#00bfff", linewidth=2.5)
            self.ax3d.set_title("3D Trajectory (Latitude-Longitude-Altitude)", color="white")
            self.ax3d.set_xlabel("Longitude (deg)", color="white")
            self.ax3d.set_ylabel("Latitude (deg)", color="white")
            self.ax3d.set_zlabel("Altitude (m)", color="white")

        self.ax3d.tick_params(colors="white")
        self.canvas3d.draw()

    def plot_map(self, df, lat_col, lon_col, station=None):
        if self.map_widget is None or df is None or df.empty:
            return
        if lat_col not in df.columns or lon_col not in df.columns:
            return

        self.map_widget.delete_all_marker()
        self.map_widget.delete_all_path()

        path_points = [(float(lat), float(lon)) for lat, lon in zip(df[lat_col], df[lon_col])]
        self.map_widget.set_path(path_points, color="#00bfff", width=3)

        start_lat, start_lon = path_points[0]
        end_lat, end_lon = path_points[-1]
        self.map_widget.set_marker(start_lat, start_lon, text="Start",
                                    marker_color_circle="#22c55e", marker_color_outside="#15803d")
        self.map_widget.set_marker(end_lat, end_lon, text="End",
                                    marker_color_circle="#ef4444", marker_color_outside="#b91c1c")

        all_lats = [p[0] for p in path_points]
        all_lons = [p[1] for p in path_points]

        if station is not None:
            s_lat, s_lon = float(station["lat"]), float(station["lon"])
            self.map_widget.set_marker(s_lat, s_lon, text=station.get("name", "Ground Station"),
                                        marker_color_circle="#f59e0b", marker_color_outside="#92400e")
            all_lats.append(s_lat)
            all_lons.append(s_lon)

        try:
            self.map_widget.fit_bounding_box((max(all_lats), min(all_lons)), (min(all_lats), max(all_lons)))
        except Exception:
            pass

    def clear_all(self):
        self.ax2d.clear()
        self.ax3d.clear()
        self.canvas2d.draw()
        self.canvas3d.draw()
        if self.map_widget is not None:
            self.map_widget.delete_all_marker()
            self.map_widget.delete_all_path()


# ==========================================================
# MAIN APPLICATION
# ==========================================================

class LLADCAConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LLA ↔ DCA Converter")
        self.root.geometry("1700x950")
        self.root.configure(bg="#0f172a")

        self.df = None
        self.output_df = None
        self.stations = []
        self.selected_station_index = None

        apply_dark_theme(self.root)
        self.build_gui()
        self.add_default_stations()

    def build_gui(self):
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self.root, textvariable=self.status_var).pack(side="bottom", fill="x")

        self.main_split = ttk.Frame(self.root)
        self.main_split.pack(fill="both", expand=True, padx=5, pady=5)
        self.build_station_sidebar(self.main_split)

        self.content_frame = ttk.Frame(self.main_split)
        self.content_frame.pack(side="left", fill="both", expand=True)

        self.control_frame = ttk.Frame(self.content_frame)
        self.control_frame.pack(fill="x", pady=(0, 5))

        self.file_frame = ttk.LabelFrame(self.control_frame, text="FILE")
        self.file_frame.pack(side="left", padx=(0, 10))
        ttk.Button(self.file_frame, text="Browse CSV", command=self.load_csv).pack(fill="x", padx=5, pady=2)
        ttk.Button(self.file_frame, text="Save Output", command=self.save_output).pack(fill="x", padx=5, pady=2)

        self.mode_frame = ttk.LabelFrame(self.control_frame, text="Conversion Mode")
        self.mode_frame.pack(side="left", padx=10)
        self.mode = tk.StringVar(value="LLA_TO_DCA")
        ttk.Radiobutton(self.mode_frame, text="LLA → DCA", variable=self.mode, value="LLA_TO_DCA", command=self.update_mapping_labels).pack(anchor="w")
        ttk.Radiobutton(self.mode_frame, text="DCA → LLA", variable=self.mode, value="DCA_TO_LLA", command=self.update_mapping_labels).pack(anchor="w")

        self.action_frame = ttk.LabelFrame(self.control_frame, text="Actions")
        self.action_frame.pack(side="left", padx=10)
        ttk.Button(self.action_frame, text="Convert", command=self.convert_data).pack(fill="x", pady=2)
        ttk.Button(self.action_frame, text="Clear Tables", command=self.clear_tables).pack(fill="x", pady=2)

        self.mapping_frame = ttk.LabelFrame(self.control_frame, text="CSV Column Configuration")
        self.mapping_frame.pack(side="left", fill="x", expand=True, padx=10)

        self.lbl_v1 = ttk.Label(self.mapping_frame, text="Time Variable:")
        self.lbl_v1.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.cbo_v1 = ttk.Combobox(self.mapping_frame, state="readonly", width=15)
        self.cbo_v1.grid(row=0, column=1, padx=5, pady=2)

        self.lbl_v2 = ttk.Label(self.mapping_frame, text="Latitude / DR:")
        self.lbl_v2.grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.cbo_v2 = ttk.Combobox(self.mapping_frame, state="readonly", width=15)
        self.cbo_v2.grid(row=0, column=3, padx=5, pady=2)

        self.lbl_v3 = ttk.Label(self.mapping_frame, text="Longitude / CR:")
        self.lbl_v3.grid(row=0, column=4, padx=5, pady=2, sticky="w")
        self.cbo_v3 = ttk.Combobox(self.mapping_frame, state="readonly", width=15)
        self.cbo_v3.grid(row=0, column=5, padx=5, pady=2)

        self.lbl_v4 = ttk.Label(self.mapping_frame, text="Altitude:")
        self.lbl_v4.grid(row=0, column=6, padx=5, pady=2, sticky="w")
        self.cbo_v4 = ttk.Combobox(self.mapping_frame, state="readonly", width=15)
        self.cbo_v4.grid(row=0, column=7, padx=5, pady=2)
        
        self.update_mapping_labels()

        self.table_frame = ttk.Frame(self.content_frame)
        self.table_frame.pack(fill="both", expand=True, pady=(0, 5))
        self.paned = ttk.PanedWindow(self.table_frame, orient="horizontal")
        self.paned.pack(fill="both", expand=True)

        self.left_frame = ttk.LabelFrame(self.paned, text="Input Data")
        self.right_frame = ttk.LabelFrame(self.paned, text="Output Data")
        self.paned.add(self.left_frame, weight=1)
        self.paned.add(self.right_frame, weight=1)

        self.input_table = DataFrameTable(self.left_frame)
        self.input_table.widget().pack(fill="both", expand=True)
        self.output_table = DataFrameTable(self.right_frame)
        self.output_table.widget().pack(fill="both", expand=True)

        self.plot_frame = ttk.LabelFrame(self.content_frame, text="Trajectory Visualization")
        self.plot_frame.pack(fill="both", expand=True)
        self.plot_tabs = PlotTabs(self.plot_frame)
        self.plot_tabs.widget().pack(fill="both", expand=True)

    def update_mapping_labels(self):
        if self.mode.get() == "LLA_TO_DCA":
            self.lbl_v1.config(text="Time:")
            self.lbl_v2.config(text="Lat (deg):")
            self.lbl_v3.config(text="Lon (deg):")
            self.lbl_v4.config(text="Alt (m):")
        else:
            self.lbl_v1.config(text="Time:")
            self.lbl_v2.config(text="DownRange (m):")
            self.lbl_v3.config(text="CrossRange (m):")
            self.lbl_v4.config(text="Altitude (m):")

    def load_csv(self):
        filename = filedialog.askopenfilename(title="Select CSV File", filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not filename: return
        try:
            self.df = pd.read_csv(filename)
            self.input_table.load_dataframe(self.df)
            
            headers = list(self.df.columns)
            for combo in [self.cbo_v1, self.cbo_v2, self.cbo_v3, self.cbo_v4]:
                combo["values"] = headers
                if headers: combo.set(headers[0])
            
            if len(headers) >= 4:
                self.cbo_v1.set(headers[0])
                self.cbo_v2.set(headers[1])
                self.cbo_v3.set(headers[2])
                self.cbo_v4.set(headers[3])

            self.status_var.set(f"Loaded: {filename}")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def convert_data(self):
        if self.df is None:
            messagebox.showwarning("Warning", "Load a CSV file first.")
            return

        t_col = self.cbo_v1.get()
        v2_col = self.cbo_v2.get()
        v3_col = self.cbo_v3.get()
        v4_col = self.cbo_v4.get()

        if not all([t_col, v2_col, v3_col, v4_col]):
            messagebox.showerror("Mapping Error", "Please verify all drop-down columns match file structural titles correctly.")
            return

        try:
            station = self.stations[self.selected_station_index]
            l_lat, l_lon, l_alt, l_az = float(station["lat"]), float(station["lon"]), float(station["alt"]), float(station["az"])
            
            results = []
            conv_mode = self.mode.get()

            for _, row in self.df.iterrows():
                t_val = row[t_col]
                if conv_mode == "LLA_TO_DCA":
                    dr, cr, alt = lla_to_dca(row[v2_col], row[v3_col], row[v4_col], l_lat, l_lon, l_alt, l_az)
                    results.append({"time_s": t_val, "down_range_m": dr, "cross_range_m": cr, "altitude_m": alt})
                else:
                    lat, lon, alt = dca_to_lla(row[v2_col], row[v3_col], row[v4_col], l_lat, l_lon, l_alt, l_az)
                    results.append({"time_s": t_val, "lat_deg": lat, "lon_deg": lon, "alt_m": alt})

            self.output_df = pd.DataFrame(results)
            self.output_df.insert(1, "launch_station", station["name"])
            self.output_table.load_dataframe(self.output_df)

            self.plot_tabs.update_available_columns(self.output_df)
            self.plot_tabs.plot_custom(self.output_df)
            self.plot_tabs.plot_3d(self.output_df, conv_mode)

            if conv_mode == "LLA_TO_DCA":
                self.plot_tabs.plot_map(self.df, v2_col, v3_col, station)
            else:
                self.plot_tabs.plot_map(self.output_df, "lat_deg", "lon_deg", station)

            self.status_var.set(f"Conversion completed using {station['name']}")
        except Exception as e:
            messagebox.showerror("Conversion Error", str(e))

    # ======================================================
    # STATION MANAGEMENT & BASE SYSTEM STRUCTS
    # ======================================================
    STATION_COLORS = ["#f59e0b", "#22c55e", "#38bdf8", "#ec4899", "#a855f7", "#ef4444", "#14b8a6", "#eab308"]

    def build_station_sidebar(self, parent):
        self.sidebar_frame = ttk.LabelFrame(parent, text="Launch Stations")
        self.sidebar_frame.pack(side="left", fill="y", padx=(0, 8))
        self.sidebar_frame.configure(width=300)
        self.sidebar_frame.pack_propagate(False)

        header = tk.Frame(self.sidebar_frame, bg="#101820")
        header.pack(fill="x", padx=6, pady=(6, 4))

        self.sidebar_count_label = tk.Label(header, text="GROUND STATIONS (0)", bg="#101820", fg="#7dd3fc", font=("Segoe UI", 9, "bold"))
        self.sidebar_count_label.pack(side="left")

        ttk.Button(self.sidebar_frame, text="+ Add Station", command=self.add_station).pack(fill="x", padx=6, pady=(0, 6))

        canvas_holder = tk.Frame(self.sidebar_frame, bg="#101820")
        canvas_holder.pack(fill="both", expand=True, padx=(6, 0), pady=(0, 6))

        self.station_canvas = tk.Canvas(canvas_holder, bg="#101820", highlightthickness=0)
        station_scrollbar = ttk.Scrollbar(canvas_holder, orient="vertical", command=self.station_canvas.yview)
        self.station_canvas.configure(yscrollcommand=station_scrollbar.set)
        self.station_canvas.pack(side="left", fill="both", expand=True)
        station_scrollbar.pack(side="right", fill="y")

        self.station_list_frame = tk.Frame(self.station_canvas, bg="#101820")
        self.station_canvas_window = self.station_canvas.create_window((0, 0), window=self.station_list_frame, anchor="nw")

        self.station_list_frame.bind("<Configure>", lambda e: self.station_canvas.configure(scrollregion=self.station_canvas.bbox("all")))
        self.station_canvas.bind("<Configure>", lambda event: self.station_canvas.itemconfigure(self.station_canvas_window, width=event.width))

        self.station_canvas.bind("<Enter>", self._bind_mousewheel)
        self.station_canvas.bind("<Leave>", self._unbind_mousewheel)

    def _bind_mousewheel(self, event):
        self.station_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.station_canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.station_canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.station_canvas.unbind_all("<MouseWheel>")
        self.station_canvas.unbind_all("<Button-4>")
        self.station_canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.station_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.station_canvas.yview_scroll(1, "units")
        else:
            self.station_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def refresh_station_sidebar(self):
        for child in self.station_list_frame.winfo_children(): child.destroy()
        for index, station in enumerate(self.stations): self.build_station_card(index, station)
        self.sidebar_count_label.config(text=f"GROUND STATIONS ({len(self.stations)})")
        self.station_canvas.update_idletasks()
        self.station_canvas.configure(scrollregion=self.station_canvas.bbox("all"))

    def build_station_card(self, index, station):
        color = self.STATION_COLORS[index % len(self.STATION_COLORS)]
        is_active = (index == self.selected_station_index)
        body_bg = "#142033" if is_active else "#0b1220"

        outer = tk.Frame(self.station_list_frame, bg=color)
        outer.pack(fill="x", padx=6, pady=5)
        inner = tk.Frame(outer, bg=body_bg, highlightthickness=1, highlightbackground=color if is_active else body_bg)
        inner.pack(fill="x", padx=(3, 0))

        header = tk.Frame(inner, bg=body_bg)
        header.pack(fill="x", padx=8, pady=(8, 2))
        tk.Label(header, text=f"STATION {index + 1:02d}", bg=body_bg, fg=color, font=("Segoe UI", 8, "bold")).pack(side="left")

        remove_label = tk.Label(header, text="✕", bg=body_bg, fg="#94a3b8", font=("Segoe UI", 9, "bold"), cursor="hand2")
        remove_label.pack(side="right")
        remove_label.bind("<Button-1>", lambda e, i=index: self.remove_station(i))

        name_entry = tk.Entry(inner, bg="#0f172a", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 11, "bold"))
        name_entry.insert(0, station["name"])
        name_entry.pack(fill="x", padx=8, pady=(0, 6))
        name_entry.bind("<FocusOut>", lambda e, i=index, w=name_entry: self.update_station_field(i, "name", w.get()))

        def make_field(parent_row, label_text, field_key, value, side):
            col = tk.Frame(parent_row, bg=body_bg)
            col.pack(side=side, fill="x", expand=True, padx=(0, 4) if side == "left" else (4, 0))
            tk.Label(col, text=label_text, bg=body_bg, fg="#94a3b8", font=("Segoe UI", 7, "bold")).pack(anchor="w")
            entry = tk.Entry(col, bg="#0f172a", fg="white", insertbackground="white", relief="flat", width=10)
            entry.insert(0, value)
            entry.pack(fill="x", expand=True)
            entry.bind("<FocusOut>", lambda e, i=index, f=field_key, w=entry: self.update_station_field(i, f, w.get()))

        row1, row2 = tk.Frame(inner, bg=body_bg), tk.Frame(inner, bg=body_bg)
        row1.pack(fill="x", padx=8, pady=(0, 4))
        row2.pack(fill="x", padx=8, pady=(0, 4))
        make_field(row1, "LATITUDE", "lat", station["lat"], "left")
        make_field(row1, "LONGITUDE", "lon", station["lon"], "right")
        make_field(row2, "ALTITUDE (m)", "alt", station["alt"], "left")
        make_field(row2, "AZIMUTH (deg)", "az", station["az"], "right")

        status_row = tk.Frame(inner, bg=body_bg)
        status_row.pack(fill="x", padx=8, pady=(2, 8))
        tk.Label(status_row, text="● ACTIVE" if is_active else "○ READY", bg=body_bg, fg="#22d3ee" if is_active else "#22c55e", font=("Segoe UI", 8, "bold")).pack(side="left")
        
        use_label = tk.Label(status_row, text="USE FOR CONVERSION", bg=body_bg, fg="#38bdf8", font=("Segoe UI", 7, "bold", "underline"), cursor="hand2")
        use_label.pack(side="right")
        use_label.bind("<Button-1>", lambda e, i=index: self.activate_station(i))

    def add_default_stations(self):
        self.stations = [
            {"name": "ITR Chandipur [LC3]", "lat": 21.437, "lon": 87.016, "alt": 10.0, "az": 90.0},
            {"name": "Dhamara Radar Stn", "lat": 20.831, "lon": 86.914, "alt": 12.0, "az": 90.0},
            {"name": "Abdul Kalam Island [LC4]", "lat": 20.754, "lon": 87.084, "alt": 5.0, "az": 135.0},
            {"name": "ITR Junput [WB]", "lat": 21.721, "lon": 87.794, "alt": 8.0, "az": 110.0},
            {"name": "Paradip Telemetry", "lat": 20.274, "lon": 86.668, "alt": 6.0, "az": 120.0},
            {"name": "DRDO ATR Chitradurga", "lat": 14.231, "lon": 76.435, "alt": 730.0, "az": 0.0},
            {"name": "Nagayalanka Range", "lat": 15.945, "lon": 80.912, "alt": 4.0, "az": 90.0},
            {"name": "SDSC Sriharikota", "lat": 13.720, "lon": 80.230, "alt": 7.0, "az": 90.0},
            {"name": "Port Blair St", "lat": 11.638, "lon": 92.714, "alt": 15.0, "az": 180.0}
        ]
        self.selected_station_index = 0
        self.refresh_station_sidebar()

    def add_station(self):
        self.stations.append({"name": f"Station {len(self.stations)+1}", "lat": 0.0, "lon": 0.0, "alt": 0.0, "az": 0.0})
        self.selected_station_index = len(self.stations) - 1
        self.refresh_station_sidebar()

    def remove_station(self, index):
        if len(self.stations) == 1: return
        self.stations.pop(index)
        self.selected_station_index = min(self.selected_station_index, len(self.stations) - 1)
        self.refresh_station_sidebar()

    def activate_station(self, index):
        self.selected_station_index = index
        self.refresh_station_sidebar()

    def update_station_field(self, index, field, raw_value):
        try:
            self.stations[index][field] = raw_value if field == "name" else float(raw_value)
        except ValueError:
            pass

    def save_output(self):
        if self.output_df is None: return
        filename = filedialog.asksaveasfilename(title="Save Output CSV", defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if filename: self.output_df.to_csv(filename, index=False)

    def clear_tables(self):
        self.df, self.output_df = None, None
        self.input_table.clear()
        self.output_table.clear()
        self.plot_tabs.clear_all()


if __name__ == "__main__":
    import ctypes
    try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception: pass
    root = tk.Tk()
    app = LLADCAConverterGUI(root)
    root.mainloop()