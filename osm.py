import streamlit as st
from OSMPythonTools.overpass import Overpass, overpassQueryBuilder, OverpassResult #typing: ignore
from OSMPythonTools.api import Api #typing: ignore
from OSMPythonTools.nominatim import Nominatim, NominatimResult #typing: ignore

class OSMConnection(st.connections.ExperimentalBaseConnection[Api]):

    api: Api
    nominatim: Nominatim
    overpass: Overpass

    def _connect(self, cache_dir: str = 'cache') -> Api:
        """Creates OSM connection objects

        Args:
            cache_dir (str): Directory where OSM APIs can cache results. Defaults to 'cache'

        Returns:
            Api: OSM API object
        """
        if cache_dir:
            from OSMPythonTools.cachingStrategy import CachingStrategy, JSON
            CachingStrategy.use(JSON, cacheDir = cache_dir)
        self.overpass = Overpass()
        self.nominatim = Nominatim()
        self.api: Api = Api()
        return self.api

    def osm_cursor(self) -> Api:
        """Retrieve underlying OSM API object
        Returns:
            Api: OSM API object
        """
        return self.api

    def nominativ_cursor(self) -> Nominatim:
        """Retrieve underlying OSM Nominativ API object
        Returns:
            Api: Nominativ API object
        """
        return self.nominatim

    def overpass_cursor(self) -> Overpass:
        """Retrieve underlying OSM Overpass API object
        Returns:
            Api: Overpass API object
        """
        return self.overpass
    
    @st.cache_data
    def lookup_place(_self, name: str, **kwargs) -> NominatimResult:
        """Geocode a location by its name using OSM's Nominativ geocoder API
        Example: 
            ```
            osm_conn = st.experimental_connection(name="osm", type=osm.OSMConnection, cache_dir="osm-cache")
            osm_conn.lookup_place("San Francisco")
            ```

        For details on parameters, see https://github.com/mocnik-science/osm-python-tools/blob/master/docs/nominatim.md)

        Args:
            name (str): Name of the location of interest

        Returns:
            NominatimResult: Nominativ resultset 
        """
        return _self.nominatim.query(name, **kwargs)

    @st.cache_data
    def reverse_geocode(_self, lat: float, lon: float, zoom: int = 18, **kwargs) -> NominatimResult:
        """Obtain a location/POI based on its coordinates using OSM's Nominativ geocoder API
        Example: 
            ```
            osm_conn = st.experimental_connection(name="osm", type=osm.OSMConnection, cache_dir="osm-cache")
            osm_conn.reverse_geocode(49.4093582, 8.694724, 10)
            ```

        For details on parameters, see https://github.com/mocnik-science/osm-python-tools/blob/master/docs/nominatim.md)

        Args:
            lat (float): Latitude of the location of interest
            lon (float): Longitude of the location of interest
            zoom (int): Zoom level (deffault: 18 - building; 10 - city; 3 - country)

        Returns:
            NominatimResult: Nominativ resultset 
        """
        return _self.nominatim.query(lat, lon, zoom=zoom, reverse=True, **kwargs)

    @st.cache_data
    def query_overpass_with_builder(_self, **kwargs) -> OverpassResult:
        """Obtain OSM element set (ways, nodes, areas or relations) using Overpass API
        Parameters passed are used in OverpassQueryBuilder directly
        For parameters, see https://github.com/mocnik-science/osm-python-tools/blob/master/docs/overpass.md

        Example: 
            ```
            osm_conn = st.experimental_connection(name="osm", type=osm.OSMConnection, cache_dir="osm-cache")
            osm_conn.query_overpass_with_builder(
                bbox=[48.1, 16.3, 48.3, 16.5], 
                elementType='node', 
                selector='"highway"="bus_stop"',
            )
            ```

        Returns:
            OverpassResult: OverPass result set
        """
        return _self.overpass.query(overpassQueryBuilder(**kwargs))
    
    @st.cache_data
    def query_overpass_raw(_self, query: str, **kwargs) -> OverpassResult:
        """Obtain OSM element set (ways, nodes, areas or relations) by a direct query to Overpass API
        For parameters, see https://github.com/mocnik-science/osm-python-tools/blob/master/docs/overpass.md
        For Overpass API query language, see https://wiki.openstreetmap.org/wiki/Overpass_API

        Example: 
            ```
            osm_conn = st.experimental_connection(name="osm", type=osm.OSMConnection, cache_dir="osm-cache")
            osm_conn.query_overpass_raw("
                (
                    node[amenity=restaurant](-20.1984472, -84.6356535, -0.0392818, -68.6519906);
                ); out center; out body;"
            )
            ```

        Args:
            query (str): Raw Overpass query

        Returns:
            OverpassResult: Overpass result set
        """
        return _self.overpass.query(query, **kwargs)