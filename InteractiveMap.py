import pandas as pd
import folium
import json
import os

from folium.plugins import MarkerCluster
from shapely.geometry import MultiPoint
from collections import defaultdict

# Function to color Volcano by Elevation
def vol_elevation(ElevData):
    if ElevData <= 1999:
        return "green"
    elif 2000 <= ElevData <= 3000:
        return "orange"
    else:
        return "red"

# Function to color Countries by Population
def pop_color_map(x):
    if x['properties']['POP2005'] < 249999:
        return "#FFF7EC"
    elif 250000 <= x['properties']['POP2005'] <= 499999:
        return "#FEE8C8"
    elif 500000 <= x['properties']['POP2005'] <= 999999:
        return "#FDD49E"
    elif 1000000 <= x['properties']['POP2005'] <= 1999999:
        return "#FDBB84"
    elif 2000000 <= x['properties']['POP2005'] <= 3999999:
        return "#FC8D59"
    elif 4000000 <= x['properties']['POP2005'] <= 7999999:
        return "#EF6548"
    elif 8000000 <= x['properties']['POP2005'] <= 15999999:
        return "#D7301F"
    elif 16000000 <= x['properties']['POP2005'] <= 31999999:
        return "#B30000"
    elif 32000000 <= x['properties']['POP2005'] <= 63999999:
        return "#990000"
    else:
        return "#7F0000"

# Load CSVs
df_volcanoes = pd.read_csv(os.path.join("Files", "cleaned_volcanoes.csv"))
df_cities = pd.read_csv(os.path.join("Files", "cleaned_locations.csv"))

# Load JSON
with open(os.path.join("Files", "world.json"), encoding="utf-8-sig") as f:
    geojson_data = json.load(f)

# Combine lat/lngs from both volcanoes and cities
all_coords = list(zip(df_volcanoes["Latitude"], df_volcanoes["Longitude"])) + \
             list(zip(df_cities["lat"], df_cities["lng"]))

MIN_LAT, MAX_LAT = -40, 40
MIN_LON, MAX_LON = -90, 90

filtered_coords = [
    (lat, lon) for lat, lon in all_coords
    if MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON
]

bounds = MultiPoint(filtered_coords).bounds  # (minx, miny, maxx, maxy)

# Define the tile URL and attribution
map_attr = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
map = folium.Map(
    location= [0, 0], 
    zoom_start= 6,
    min_zoom=2,
    max_zoom=7,
    max_bounds=True,
    control_scale=True
    )

folium.TileLayer(tiles="CartoDB Voyager",
                 attr=map_attr,
                 name="CartoDB Voyage",
                 control=False,
                 #no_wrap=True,
                 min_native_zoom=2,
                 max_native_zoom=7
                 ).add_to(map)

# Volcanoes group
fg_volcanoes = folium.FeatureGroup(name="All Volcanoes", show=False)
volcano_country_groups = {}

for _, row in df_volcanoes.iterrows():
    popup_html_volcanoes = f"""
    <b>Volcano:</b> {row['Volcano Name']}<br>
    <b>ID Number:</b> {row['Number']}<br>
    <b>Country:</b> {row['Country']}<br>
    <b>Elevation:</b> {row['Elevation (m)']} m
    """

    fg_volcanoes.add_child(folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=6,
        popup=folium.Popup(popup_html_volcanoes, max_width=300), 
        fill_color=vol_elevation(row['Elevation (m)']),
        fill_opacity=0.75,
        fill=True,
        color="grey",
        weight=1
        ))
    
    country = row["Country"]
    if country not in volcano_country_groups:
        volcano_country_groups[country] = folium.FeatureGroup(name=f"{country} - Volcanoes", show=False)


    volcano_country_groups[country].add_child(folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=6,
        popup=folium.Popup(popup_html_volcanoes, max_width=300), 
        fill_color=vol_elevation(row['Elevation (m)']),
        fill_opacity=0.75,
        fill=True,
        color="grey",
        weight=1
        ))

# Cities group
fg_cities = folium.FeatureGroup(name="All Cities", show=False,)
cities_country_group = {}
city_cluster = MarkerCluster()

for _, row in df_cities.groupby('country').head(150).iterrows():
    popup_html_cities = f"""
    <b>City:</b> {row['city']}<br>
    <b>Country:</b> {row['country']}<br>
    """

    city_cluster.add_child(folium.Marker(
        location=[row['lat'], row['lng']], 
        popup=folium.Popup(popup_html_cities, max_width=300), 
        icon=folium.Icon(color="blue"),
        ))
    
    country = row["country"]
    if country not in cities_country_group:
        cities_country_group[country] = folium.FeatureGroup(name=f"{country} - Cities", show=False)
    
    cities_country_group[country].add_child(folium.Marker(
        location=[row['lat'], row['lng']], 
        popup=folium.Popup(popup_html_cities, max_width=300), 
        icon=folium.Icon(color="blue"),
        ))

fg_cities.add_child(city_cluster)

# Population mapping and coloring
fg_population = folium.FeatureGroup(name="Population", show=True)
fg_population.add_child(folium.GeoJson(data=geojson_data,
                        style_function=lambda x: {
                            'fillColor':pop_color_map(x),
                            'color': "black",
                            'weight': 1
                            }))

# Adds these to the layer control as a whole not grouped by country
map.add_child(fg_volcanoes)
map.add_child(fg_cities)
map.add_child(fg_population)

# Makes Cities and Volcanoes grouped by country and adds it to the layer control
all_groups = []

for country, group in volcano_country_groups.items():
    all_groups.append((f"{country} - Volcanoes", group))
for country, group in cities_country_group.items():
    all_groups.append((f"{country} - Cities", group))
for name,group in sorted(all_groups, key=lambda x: x[0]):
    map.add_child(group)

map.options['maxBounds'] = [[-86.5,-181.5], [86.5, 181.5]]

# A work around to get min/max zooming and left and right panning to work correctly
map.get_root().html.add_child(folium.Element(f"""
<script>
    window.addEventListener('load', function () {{
        const mapContainer = document.querySelector('.leaflet-container');
        if (!mapContainer) return;

        const observer = new MutationObserver(() => {{
            const leafletMap = Object.values(window).find(v => v instanceof L.Map);
            if (leafletMap) {{
                // Fit to bounds
                const bounds = L.latLngBounds(
                    [{bounds[1]}, {bounds[0]}],
                    [{bounds[3]}, {bounds[2]}]
                );
                leafletMap.fitBounds(bounds, {{ padding: [20, 20] }});

                // Lock zoom limits
                leafletMap.options.minZoom = 2;
                leafletMap.options.maxZoom = 7;
                leafletMap.setMinZoom(2);
                leafletMap.setMaxZoom(7);

                observer.disconnect();
            }}
        }});

        observer.observe(mapContainer, {{ childList: true, subtree: true }});
    }});
</script>
"""))
map.add_child(folium.LayerControl())
#map.get_root().html.add_child(folium.Element('<h3 align="center">World Volcanoes & Cities Map</h3>'))


# Adding a layercontrol search dropdown and zoom to country
all_country_names = sorted(set(list(volcano_country_groups.keys()) + list(cities_country_group.keys())))

map.get_root().html.add_child(folium.Element(f"""
<link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css" rel="stylesheet" />
<script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script>

<div style="position: fixed; top: 70px; left: 60px; z-index: 9999; background: white; padding: 10px; border-radius: 8px;">
    <label for="layer-select">Select Country:</label>
    <select id="layer-select" style="width: 200px;">
        <option value="" disabled selected>-- Select Country --</option>
        <option value="__none__">-- None --</option>
        {''.join(f'<option value="{name}">{name}</option>' for name in all_country_names)}
    </select>
</div>

<script>
    window.addEventListener("load", function () {{
        setTimeout(() => {{
            const select = $('#layer-select');
            if (!select.length) {{
                console.warn("Dropdown not found.");
                return;
            }}

            select.select2();
            select.val("").trigger('change');

            select.on('change', function (e) {{
                const selected = e.target.value;
                console.log("Selected:", selected);

                const countryLayers = [...document.querySelectorAll('.leaflet-control-layers-overlays input')];

                if (!countryLayers.length) {{
                    console.warn("No layer checkboxes found!");
                    return;
                }}

                // ✅ Show/hide appropriate layers
                countryLayers.forEach(input => {{
                    const parent = input.parentElement;
                    if (!parent) return;
                    const label = parent.textContent.trim();

                    let shouldBeChecked = false;
                    if (selected === "__none__") {{
                        shouldBeChecked = false;
                    }} else if (selected) {{
                        shouldBeChecked = label.toLowerCase().includes(selected.toLowerCase());
                    }}

                    if (input.checked !== shouldBeChecked) {{
                        input.click();
                        console.log("Toggled:", label);
                    }}
                }});

                // ✅ Manual zoom to center after a short delay
                setTimeout(() => {{
                    const leafletMap = Object.values(window).find(v => v instanceof L.Map);
                    if (leafletMap) {{
                        const visibleMarkers = [];

                        leafletMap.eachLayer(function(layer) {{
                            if (layer instanceof L.Marker && leafletMap.hasLayer(layer)) {{
                                visibleMarkers.push(layer.getLatLng());
                            }}
                        }});

                        if (visibleMarkers.length > 0) {{
                            let avgLat = 0;
                            let avgLng = 0;

                            visibleMarkers.forEach(latlng => {{
                                avgLat += latlng.lat;
                                avgLng += latlng.lng;
                            }});

                            avgLat /= visibleMarkers.length;
                            avgLng /= visibleMarkers.length;

                            // 🎯 Move map manually to center of visible markers at zoom 4
                            leafletMap.setView([avgLat, avgLng], 4);
                            console.log("Manually centered to:", avgLat, avgLng);
                        }} else {{
                            console.log("No visible markers to center to");
                        }}
                    }}
                }}, 200); // Wait 200ms to let layers toggle
            }});
        }}, 500);
    }});
</script>
"""))
#map.get_root().render()

map.save(os.path.join("docs", "InteractiveMap.html"))