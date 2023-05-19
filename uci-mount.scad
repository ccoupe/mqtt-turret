bh=3;
//sl=23;
sw=12;
//sh=15;
module mount() {
    difference() {
        translate([3,0,0]) cube([6+20,12,42],true);
        translate([-3,0,0]) cube([7+11,12,36],true);
        translate([-33/2+8/2,0,34/2]) rotate([0,0,90]) union() {
            translate([0,0,0.5]) cylinder(r=8/2,h=3,$fn=40);
            translate([0,0,-1.1]) cylinder(r=1.5,h=6,$fn=40);
            translate([0,-6.5,1.5]) cube([6,18,4],true);
        }
        translate([-33/2+8/2,0,-33/2-6]) rotate([0,0,90]) cylinder(r=1.5,h=6,$fn=40);
        translate([2.5,0,0]) rotate([0,90,0]) cylinder(r=3,h=14+11,$fn=50);
    }
    // diode barrel
    translate([0.5+15,1.5,0]) rotate([0,90,0]) 
      difference() {
        cylinder(r=8,h=35,$fn=50);
        translate([0,4,7]) cube([17,8,58],true);
        cylinder(r=6,h=35,$fn=50);
    }
    // Oak-D Lite camera mount
    translate([-10,0,0]) camera_mount();
}

module camera_mount() {
  difference() {
    union() {
      translate([0,4,-5]) rotate([90,0,90]) cube([20,10,5]);
      translate([0,24,6]) rotate([90,90,90]) union() {
        difference() {
          cube([45,5,20]);
          translate([33,8,11]) rotate([90,0,0]) cylinder(r=4,h=10);
        }
       translate([0,2,0]) rotate ([0,0,0]) cube([4,10,4]);
      }
    }
  }
}

difference () {
  // import 
  import("PanTilt_Camerabottom.stl");
  translate([-32,29.5,-1]) difference () cylinder(r=1.5,h=4,$fn=20);
  translate([-19,29.5,-1]) difference () cylinder(r=1.5,h=4,$fn=20);
  // remove some material in the back - optional?
  *translate([-35,43,1]) cube([20,2,12]);
}
*translate([-35,43,0]) cube([20,2,12]);

translate([-26,40,10]) rotate([0,-90,0]) mount();

