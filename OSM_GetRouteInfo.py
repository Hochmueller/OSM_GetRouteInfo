#https://github.com/MKuranowski/pyroutelib3
import pyroutelib3
from pyroutelib3 import Router # Import the router
#https://github.com/MatthewDaws/TileMapBase
import matplotlib.pyplot as plt
import tilemapbase
import requests
import json
import os


class tEst(object):
    def __init__(self,localFile):
        # https://wiki.openstreetmap.org/wiki/Routing
        pyroutelib3.TYPES["car"]['weights']['motorway'] = 20
        pyroutelib3.TYPES["car"]['weights']['trunk'] = 10
        pyroutelib3.TYPES["car"]['weights']['primary'] = 1
        pyroutelib3.TYPES["car"]['weights']['secondary'] = 1
        pyroutelib3.TYPES["car"]['weights']['tertiary'] = 1
        pyroutelib3.TYPES["car"]['weights']['unclassified'] = 1
        pyroutelib3.TYPES["car"]['weights']['residential'] = 0.5
        pyroutelib3.TYPES["car"]['weights']['track'] = 0
        pyroutelib3.TYPES["car"]['weights']['service'] = 0
        if localFile:
            self.router=Router("car",localFile)
        else:
            self.router = Router("car")


    def routeF(self, p1Lag, p1Long, p2Lag, p2Long):
        self.s=(p1Lag,p1Long)
        self.e=(p2Lag,p2Long)

        start = self.router.findNode(self.s[0], self.s[1])
        end = self.router.findNode(self.e[0], self.e[1])

        self.filesName="{}_{}".format(start,end)
        routeFile=self.filesName+"_route.json"

        #if file already available load it
        if os.path.isfile(routeFile):
            with open(routeFile,'r') as f:
                (self.route,self.routeLatLons)=json.load(f)
                #self.routeLatLons = list(map(self.router.nodeLatLon, self.route))
        #if no file is available calcualte route and store it
        else:
            status, self.route = self.router.doRoute(start, end)
            if status == 'success':
                self.routeLatLons = list(map(self.router.nodeLatLon, self.route))  # Get actual route coordinates
                with open(routeFile,'w') as f:
                    json.dump([self.route,self.routeLatLons],f)
            else:
                raise Exception("could not find a route from two points p1: ({}) p2: ({}). Status:{}".format(start,end,status))

    def printRoute(self,dpi,width):
        tilemapbase.start_logging()
        tilemapbase.init(create=True)
        t = tilemapbase.tiles.build_OSM()

        if self.s[0] < self.e[0]:
            south = self.s[0]; north = self.e[0]
        else:
            south = self.e[0]; north = self.s[0]

        if self.s[1] < self.e[1]:
            east = self.s[1]; west = self.e[1]
        else:
            east = self.e[1]; west = self.s[1]

        degree_range = 0.1
        extent = tilemapbase.Extent.from_lonlat(east - degree_range, west + degree_range,
                                                south - degree_range, north + degree_range)

        fig, ax = plt.subplots(figsize=(8, 8), dpi=dpi)


        plotter = tilemapbase.Plotter(extent, t, width=width)
        plotter.plot(ax, t)

        for i in self.routeLatLons:
            x, y = tilemapbase.project(i[1], i[0])
            ax.scatter(x, y, marker=".", color="black", linewidth=2)
        plt.show()




    def getWay(self):
        #https://www.openstreetmap.org/node/34817889 -> To see node in osm.org
        #http://overpass-api.de/api/interpreter?data=[out:json];node(34817889);way(bn);out; 
        #-> what we are doing with request.
        wayfile=self.filesName+"_way.json"
        if os.path.isfile(wayfile):
            with open(wayfile,'r') as f:
                self.way=json.load(f)
        else:
            data = []
            overpass_url = "http://overpass-api.de/api/interpreter"
            for i in self.route:
                overpass_query = """
                [out:json];
                (node({});
                 way(bn);
                );
                out center;
                """.format(i)
                while True:
                    try:
                        response = requests.get(overpass_url,
                                                params={'data': overpass_query})
                        data.append(response.json())
                        break
                    except: 
                        print("error {}".format(i))
                

            #remove not needed information
            elements = []
            for i in range(0, len(data)):
                elements.append(data[i]['elements'])

            #filter ways a bit
            ways = []
            for i in elements:
                ways.append([])
                for j in i:
                    if j['type'] == 'way':
                        if 'tags' in j:
                            if 'highway' in j['tags']:
                                if j['tags']['highway'] != 'footway' \
                                        and j['tags']['highway'] != 'raceway' \
                                        and j['tags']['highway'] != 'bridleway' \
                                        and j['tags']['highway'] != 'steps' \
                                        and j['tags']['highway'] != 'path' \
                                        and j['tags']['highway'] != 'service':
                                    ways[-1].append(j)

            #algorithm to detect correct way out of multible ways of singel point
            #initail point
            way = []
            for i in range(0, len(ways[0])):
                for j in range(0, len(ways[1])):
                    if ways[0][i]['id'] == ways[1][j]['id']:
                        way.append(ways[0][i])
                        break

            #following points
            cnt = 0
            for i in range(1, len(ways)):
                if cnt > 1:
                    raise Exception("can't detect correct way point!")

                cnt = 0
                for j in range(0, len(ways[i])):
                    for k in range(0, len(ways[i - 1])):
                        if ways[i][j]['id'] == ways[i - 1][k]['id']:
                            way.append(ways[i][j])
                            cnt += 1

            self.way=way
            with open(wayfile,'w') as f:
                json.dump(self.way,f)

    def getMaxSpeed(self):
        speed = []
        for i in self.way:
            if 'maxspeed' in i['tags'] and i['tags']['maxspeed'] != 'signals':
                speed.append(int(i['tags']['maxspeed']))
            else:
                if i['tags']['highway'] == 'motorway':
                    if 'tunnel' in i['tags'] and i['tags']['tunnel'] == 'yes':
                        speed.append(100)
                    else:
                        speed.append(130)
                elif i['tags']['highway'] == 'motorway_link':
                    speed.append(100)
                elif i['tags']['highway'] == 'trunk':
                    speed.append(100)
                elif i['tags']['highway'] == 'tunk_link':
                    speed.append(100)
                elif i['tags']['highway'] == 'primary':
                    speed.append(100)
                elif i['tags']['highway'] == 'primary_link':
                    speed.append(80)
                elif i['tags']['highway'] == 'secondary':
                    speed.append(100)
                elif i['tags']['highway'] == 'secondary_link':
                    speed.append(80)
                elif i['tags']['highway'] == 'tertiary':
                    speed.append(70)
                elif i['tags']['highway'] == 'tertiary_link':
                    speed.append(50)
                elif i['tags']['highway'] == 'unclassified':
                    speed.append(70)
                elif i['tags']['highway'] == 'residential':
                    speed.append(50)
                else:
                    raise Exception("can't find max speed of route:{}".format(i))

        self.maxSpeed=speed

    def getDist(self):
        # list of distance between nodes
        self.distance = []
        #for i in range(0, len(self.routeLatLons) - 1):
        #    self.distance.append(self.router.distance(self.routeLatLons[i], self.routeLatLons[i + 1]))
        for i in range(0, len(self.way)-1):
            self.distance.append(self.router.distance([self.way[i]['center']['lat'],self.way[i]['center']['lon']],[self.way[i+1]['center']['lat'],self.way[i+1]['center']['lon']]))
                #self.routeLatLons[i], self.routeLatLons[i + 1]))
