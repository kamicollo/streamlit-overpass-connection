import streamlit as st
from OSMPythonTools.overpass import Overpass, overpassQueryBuilder
import osm
import importlib
importlib.reload(osm)
import h3
H3_LEVEL = 12
import pandas as pd
import itertools as itt
import pydeck as pdk

st.set_page_config(layout="wide")

st.header("OSM Connection demo app")
st.markdown("""
This demo app showcases Open Street Map API support using `st.experimental_connection`.

## Usage notes

The basic usage of the OSM connection is:

```python
import osm
osm_conn = st.experimental_connection(name="osm", type=osm.OSMConnection, cache_dir="osm-cache")
#geocode a place
sf = os_conn.lookup_place("San Francisco") 
#find a point of interest at given coordinates
os_conn.reverse_geocode(lat=10, lon=10, zoom=18) 
#find all restaurants in SF
os_conn.query_overpass_with_builder(area=sf, elementType='node', selector='"amenity"="restaurant"') 
#find all restaurants in a bounding box using raw Overpass query
os_conn.query_overpass_raw("(node[amenity=restaurant](-20.1984472, -84.6356535, -0.0392818, -68.6519906);) out body;")
```

Underlying API objects can be retrieved with `osm_cursor()`, `nominativ_cursor()` and `overpass_cursor()` methods.

The OSM APIs do not require credentials. The streamlit connection uses OSMPythonTools, so you'll have to install it
```pip install OSMPythonTools```

OSMPythonTools has its own caching strategy. 
To change the folder to which cache results are saved, pass `cache_dir` parameter to the streamlit connection.

## Demo

This demo uses both Nominativ and Overpass APIs. It allows you choosing an arbitrary location around the world, 
retrievings POIs of selected categories, which are then visualized on a map.

Have fun!

""")

osm_conn = st.experimental_connection(name="osm", type=osm.OSMConnection, cache_dir="osm-cache")

poi_categories = {
    'Clinics and Hospitals': ('amenity', ['clinic', 'hospital']),
    'Schools and Kindergartners': ('amenity', ['school', 'kindergarten']),
    'Restaurants': ('amenity', ['restaurant']),
    'Cinemas and Theaters': ('amenity', ['cinema', 'theatre']),
    'Grocery stores and supermarkets': ('shop', ['convenience', 'greengrocer', 'seafood', 'mall', 'wholesale', 'supermarket'])
}

poi_colors = {
    'Clinics and Hospitals': [141,211,199],
    'Schools and Kindergartners': [255,255,179],
    'Restaurants': [190,186,218],
    'Cinemas and Theaters': [251,128,114],
    'Grocery stores and supermarkets': [128,177,211] 
}

def show_rectangle(context, rgb_colors, label):
    context.write(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="220" height="30">
            <g>      
                <rect x=0 y=0 width="100%" height="100%" style="fill:rgb({', '.join([str(c) for c in rgb_colors])})" />
                <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="Verdana" font-size="10" fill="black">{label}</text>
            </g>
            </svg>""", 
        unsafe_allow_html=True
    )

place_name = st.text_input("Choose a city/town/village", on_change=st.balloons)
if place_name:    
    places = [place for place in osm_conn.lookup_place(place_name).toJSON() if place["class"] in ['boundary', 'place']]
    if len(places) > 1:        
        selection = st.selectbox(
            "Found several candidates - choose one",
            options = places,
            format_func= lambda p: p['display_name'],
        )
    elif len(places) == 1:
        selection = places[0]
    else:
        st.warning("No places with such name found.. try again?")
        selection = None

    if selection:                        
        choices = st.multiselect(
            label="Select categories of POIs to retrieve",
            options=poi_categories.items(),
            format_func= lambda p: p[0]
        )
        if len(choices):
            selectors = []
            for _, choice in choices:
                selectors += [k + "=" + v for k,v in zip([choice[0]] * len(choice[1]), choice[1])]

            lat1, lat2, lon1, lon2 = selection['boundingbox']
            bbox_string = ", ".join([lat1, lon1, lat2, lon2])
            nodes = [f"""node[{selector}]({bbox_string});""" for selector in selectors]
            query = """
            (
                {}
            ); out center; out body;""".format("\n ".join(nodes))
                        
            results =  osm_conn.query_overpass_raw(query)
            if results.countElements() == 0:
                st.warning("No points of interest found - try another category or choose a different location")
            else:
                st.info(f"Found a total of {results.countElements()} points of interest in {selection['display_name']}")
                if results.countElements() > 10_000:
                    st.warning("Displaying only the first 10,000 results")
                pois = [{                
                    "Name": poi.tag("name"),                
                    "hex": h3.geo_to_h3(poi.lat(), poi.lon(), H3_LEVEL),  
                    "color": poi_colors[[name for name, vals in poi_categories.items() if len(set(poi.tags().values()).intersection(set(vals[1]))) > 0][0]],
                    "tags": "<br>".join([k + ": " + v for k,v in poi.tags().items() if 'addr' not in k and 'name' not in k])
                } for poi in results.nodes()[:10_000] if poi.tag("name") is not None]            
                
                layer = pdk.Layer(
                    "H3HexagonLayer",
                    data=pd.DataFrame(pois),
                    pickable=True,
                    stroked=True,
                    filled=True,
                    extruded=False,
                    get_hexagon="hex",
                    get_fill_color="color",
                    get_line_color=[255, 255, 255],
                    line_width_min_pixels=2,
                )

                # Set the viewport location
                view_state = pdk.ViewState(
                    latitude=float(selection['lat']), 
                    longitude=float(selection['lon']), 
                    zoom=15, bearing=0, pitch=30
                )            
                # Render
                r = pdk.Deck(
                    layers=[layer], 
                    initial_view_state=view_state, 
                    tooltip={"html": "<b>Name: {Name}<b><br>{tags}"}, 
                    map_style=None
                )
                for column, (name, color) in zip(st.columns(len(poi_colors)), poi_colors.items()):
                    show_rectangle(column, color, name)
                st.pydeck_chart(r)
            