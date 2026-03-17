use std::f64::consts::PI;

pub fn haversine_distance(lat1: f64, lon1: f64, lat2: f64, lon2: f64) -> f64 {
    let r = 6371.0; // Earth's radius in km
    let dlat = (lat2 - lat1).to_radians();
    let dlon = (lon2 - lon1).to_radians();
    let a = (dlat / 2.0).sin().powi(2) + lat1.to_radians().cos() * lat2.to_radians().cos() * (dlon / 2.0).sin().powi(2);
    let c = 2.0 * a.sqrt().atan2((1.0 - a).sqrt());
    r * c
}

pub fn evaluate_geo_velocity(
    lat1: f64,
    lon1: f64,
    ts1: f64,
    lat2: f64,
    lon2: f64,
    ts2: f64,
    speed_threshold_kmh: f64,
) -> (bool, f64) {
    let dist_km = haversine_distance(lat1, lon1, lat2, lon2);
    let time_diff_hours = (ts2 - ts1).abs() / 3600.0;
    
    if time_diff_hours == 0.0 {
        return (dist_km > 1.0, 0.0); // If same second but different location, highly suspicious
    }
    
    let speed_kmh = dist_km / time_diff_hours;
    (speed_kmh > speed_threshold_kmh && dist_km > 50.0, speed_kmh)
}
