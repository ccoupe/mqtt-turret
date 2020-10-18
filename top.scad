// Punch Capaciter and Pwr Mount holes into 
capdia = 11.5;
pwr_w = 6.9;
pwr_d = 9.0;
pwr_h = 4.5;
fl = "fixed-mesh-top.stl";

 difference() {
    import(fl);
    union() {
        translate([-50,71.5,0]) {
            cube([pwr_w,pwr_d,pwr_h]);
        }
        
        translate([-47,96,0]) {
            cylinder(d=capdia, h=4.5);
        }
    } 
}
