LLA ↔ DCA Converter - Professional Tkinter GUI Application
==========================================================

An advanced, dark-themed desktop utility designed for aerospace engineers, geodesists, and GIS professionals to seamlessly convert trajectories between Geodetic Coordinates (Latitude, Longitude, Altitude - LLA) and Down-Range Coordinate System (DCA) coordinates based on the WGS84 reference ellipsoid.

----------------------------------------------------------
Features
----------------------------------------------------------
1. Dual Conversion Modes:
   - LLA → DCA: Converts geodetic latitude, longitude, and altitude to local down-range, cross-range, and altitude relative to a selected ground station.
   - DCA → LLA: Reconstructs standard geodetic coordinates from local down-range and cross-range measurements via iterative WGS84 mapping.

2. Dynamic Ground Station Sidebar:
   - Comes preloaded with major test ranges and telemetry stations (e.g., ITR Chandipur, SDSC Sriharikota, Abdul Kalam Island, ATR Chitradurga).
   - Scrollable, interactive sidebar UI with real-time status indicators ("ACTIVE" vs "READY").
   - Dynamic adding, updating, and removing of custom ground stations (Latitude, Longitude, Altitude, and Launcher Reference Azimuth).

3. Flexible Data Ingestion & Mapping:
   - Ingest any custom flight data via standard CSV files.
   - Smart dropdown column configuration mapping dynamically maps time, latitude/down-range, longitude/cross-range, and altitude fields from raw CSV headers.

4. Built-in Analytics & Visualization Suite:
   - Custom 2D Plotting: Interactively plot any numeric column against another (e.g., Altitude vs Time).
   - 3D Trajectory Visualization: Automatic 3D line plots depicting true spatial flight paths.
   - Interactive Dark Map: Integrates a live GIS map provider (via tkintermapview) rendering paths, start points, end points, and station milestones using a custom dark theme.

5. Production Exporting:
   - Export structured conversion output to clean CSV logs.
   - Direct-to-PDF high-resolution vector export for custom 2D analytical charts.

----------------------------------------------------------
Mathematical Reference
----------------------------------------------------------
- Ellipsoid Constants (WGS84): 
  * Semi-major axis (a) = 6,378,137.0 m
  * Flattening (f) = 1 / 298.257223563
- Transformation Pipeline:
  * LLA ↔ ECEF (Earth-Centered, Earth-Fixed) ↔ ENU (East, North, Up) ↔ DCA (Down-Range, Cross-Range, Altitude)

----------------------------------------------------------
Prerequisites & Dependencies
----------------------------------------------------------
Ensure you have Python 3.7+ installed. The following libraries are required:

  pip install pandas numpy matplotlib tkintermapview

*Note: If 'tkintermapview' is missing, the application will degrade gracefully by disabling the map tab while keeping all chart and calculation features active.*

----------------------------------------------------------
How to Run
----------------------------------------------------------
1. Clone or copy the `LLA_DCA_conversion.py` script into your workspace.
2. Launch the GUI tool from your terminal:

   python LLA_DCA_conversion.py

----------------------------------------------------------
Step-by-Step Usage Guide
----------------------------------------------------------
1. Configure Station: Select a pre-loaded ground station from the left sidebar or click "+ Add Station" to specify a custom coordinate center and azimuth angle. Click "USE FOR CONVERSION".
2. Import Data: Click "Browse CSV" under the File frame to import your raw telemetry or simulation log.
3. Map Columns: In the "CSV Column Configuration" area, select which spreadsheet headers correspond to your Time, Horizontal, and Vertical fields.
4. Execute: Choose the conversion orientation (LLA → DCA or DCA → LLA) and click "Convert".
5. Visualize & Save: Explore the generated paths in the Charts and Trajectory Map tabs. Click "Save Output" to save the conversion spreadsheet or "Save Plot" to export the graph to a PDF report.

----------------------------------------------------------
License
----------------------------------------------------------
This tool is open-source and intended for engineering evaluation, simulation analysis, and aerospace telemetry processing.
