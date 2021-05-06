function initMap() {
    var map = new google.maps.Map(document.getElementById('map'), {
        // Roughly centre the map so that all PoPs are in view
        center: new google.maps.LatLng(30, -120),
        zoom: 2,
        mapTypeId: 'hybrid'
    });
    var infoWindow = new google.maps.InfoWindow();
    map.data.setStyle({
       strokeColor: '#66F0F0',
       strokeOpacity: 0.4,
       strokeWeight: 5
    });
    map.data.loadGeoJson(
        "/static/netmap.geojson"
    );

    map.data.addListener("click", (event) => {
        var feat = event.feature;
        var content = "<span style=\"font-size:large;font-weight:500\">" + feat.getProperty('title') + "</span><br>" + feat.getProperty('description');

        infoWindow.setContent(content);
        infoWindow.setPosition(event.latLng);
        if (feat.getGeometry().getType() === "Point") {
            infoWindow.setOptions({pixelOffset: new google.maps.Size(0, -32)});
        } else {
            infoWindow.setOptions({pixelOffset: new google.maps.Size(0, 0)});
        }
        infoWindow.open(map);
    });
}
