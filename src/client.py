import overpy
import geopandas as gpd
import shapely.geometry as geometry
from time import sleep


"""
Useful links: 
List of keys, tags and values in OSM: https://taginfo.openstreetmap.org/
Test queries with overpass turbo: https://overpass-turbo.eu/
"""

class Client:


    def __init__( self, chunk_size=None, url=None, max_retries=None, retry_timeout=None ):

        """"
        constructor
        """

        # create overpass api object
        self._api = overpy.Overpass(    read_chunk_size=chunk_size, 
                                        url=url, 
                                        xml_parser=2, 
                                        max_retry_count=max_retries, 
                                        retry_timeout=retry_timeout )
        return


    def getQuery( self, query, max_retries=3 ):

        """
        get query
        """

        response = None

        # loop until response or max retries exceeded
        attempts = 0
        while True:
            try:
                # forward query to server
                response = self._api.query(query)
                break
            except overpy.exception.OverpassTooManyRequests:
                print ( 'Overpass Too Many Requests - retrying in 60 seconds ... ' )
                sleep(10*6)
            except overpy.exception.OverpassBadRequest as error:
                print ( 'Overpass Bad Request Error: {} '.format ( error ) )
                break
            except BaseException as error:
                print ( 'General Error: {} '.format ( error ) )
                break

            # exit on max retries
            attempts += 1
            if attempts > max_retries:
                break

        return response


    def getWaysInBoundingBox( self, key, bbox, value=None, tags=[] ):

        """
        get ways inside bounding box
        """

        # overpass query to retrieve way features within bbox
        condition = f"['{key}']" if value is None else f"['{key}'='{value}']"
        query = f"""
                    way
                    {condition}
                    (""" + ','.join(map(str,bbox)) + """);
                    /*added by auto repair*/
                    (._;>;);
                    /*end of auto repair*/
                    out;
                """

        return self.getDataFrame( self.getQuery( query ), tags )


    def getWaysAroundPoint( self, key, point, buffer, value=None, tags=[] ):

        """
        get ways around point
        """

        # get coords
        latitude = point[ 'latitude' ]
        longitude = point[ 'longitude' ]

        # overpass query to retrieve way features around point
        condition = f"['{key}']" if value is None else f"['{key}'='{value}']"
        query = f"""
                    way
                    {condition}
                    (around:{buffer}, {latitude},{longitude});
                    /*added by auto repair*/
                    (._;>;);
                    /*end of auto repair*/
                    out;
                """

        return self.getDataFrame( self.getQuery( query ), tags )


    def getNodesInCountry( self, key, alpha3, value=None, tags=[] ):

        """
        get nodes in country
        """

        # overpass query to retrieve way features around point
        condition = f"node['{key}']" if value is None else f"node['{key}'='{value}']"
        query = f"""
                    (area['ISO3166-1:alpha3'='{alpha3}'];) ->.a;
                    {condition}
                    (area.a);
                    /*added by auto repair*/
                    (._;>;);
                    /*end of auto repair*/
                    out;
                """

        return self.getDataFrame( self.getQuery( query ), tags )


    def getDataFrame( self, result, tags=[] ):

        """
        convert result into geo dataframe
        """

        def getWayRecords():

            """
            get way records
            """

            # parse result
            records = []
            for way in result.ways:

                # create a list of node coordinates
                coords = []
                for node in way.get_nodes():
                    coords.append((node.lon,node.lat))

                # package up data + convert node list to polygon
                data = { 'id' : way.id, 'geometry' : geometry.Polygon( coords ) }
                for tag in tags:            
                    data[ tag ] = way.tags.get( tag )

                # append to list
                records.append( data )

            return records


        def getNodeRecords():

            """
            get node records
            """

            records = []
            for node in result.nodes:

                # package up data + convert node list to polygon
                data = { 'id' : node.id, 'geometry' : geometry.Point( node.lon,node.lat ) }
                for tag in tags:            
                    data[ tag ] = node.tags.get( tag )

                # append to list
                records.append( data )

            return records

        # generate record list
        records = getWayRecords()
        if len( records ) == 0:            
            records = getNodeRecords()

        # encode as geodataframe
        return gpd.GeoDataFrame( records, crs='EPSG:4326' )


    @staticmethod
    def runTests():

        """
        tests to validate class functionality
        """

        def test1():

            """
            ways inside bounding box
            """

            # bbox encompassing sussex county
            bbox = (50.72222,-0.9575,51.16722,0.04527778)
            df = obj.getWaysInBoundingBox( 'amenity', bbox, value='school', tags=[ 'name', 'addr:postcode' ] )

            print ( df.head(10) )
            print ( len( df ) )

            return


        def test2():

            """
            ways inside bounding box
            """

            # hospitals within 20km distance of point
            point = { 'latitude' : 51.4545, 'longitude' : -2.5879 }
            buffer = 20000

            df = obj.getWaysAroundPoint( 'amenity', point, buffer, value='hospital', tags=[ 'name', 'addr:postcode' ] )

            print ( df.head(10) )
            print ( len( df ) )

            return


        def test3():

            """
            country-specific query
            """

            # all Italian schools (!)
            df = obj.getNodesInCountry( 'amenity', 'ITA', value='school' )

            print ( df.head(10) )
            print ( len( df ) )

            return

        # create client and run tests
        obj = Client()
        test1()
        test2()
        test3()

        return


#Client.runTests()
