module mount() {
    difference() {
        cube([6+11,12,44],true);
        translate([-3,0,0]) cube([7+11,12,36],true);
        translate([-33/2+8/2,0,34/2]) rotate([0,0,90]) union() {
            translate([0,0,0.5]) cylinder(r=8/2,h=3,$fn=40);
            translate([0,0,-1.1]) cylinder(r=1.5,h=6,$fn=40);
            translate([0,-6.5,1.5]) cube([6,18,4],true);
        }
        translate([-33/2+8/2,0,-33/2-6]) rotate([0,0,90]) cylinder(r=1.5,h=6,$fn=40);
        translate([2.5,0,0]) rotate([0,90,0]) cylinder(r=3,h=14+11,$fn=50);
    }
    translate([1.5+7,0,0]) rotate([0,90,0]) difference() {
        cylinder(r=6,h=14,$fn=50);
        translate([0,4,7]) cube([14,5,14],true);
        cylinder(r=3.5,h=14,$fn=50);
    }
}
union() {
translate([50,-10,-40]) rotate([90,180,00]) import("PanTilt_Arm.stl");
translate([-7.75,-10,-0.8]) rotate([90,0,90]) mount();
}