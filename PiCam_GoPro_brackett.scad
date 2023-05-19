$fa = 2;
$fs = 0.25;
Extra_Mount_Depth = 6;

module nut_hole()
{
	rotate([0, 90, 0]) // (Un)comment to rotate nut hole
	rotate([90, 0, 0])
		for(i = [0:(360 / 3):359])
		{
			rotate([0, 0, i])
				cube([4.6765, 8.1, 5], center = true);
		}
}

module flap(Width)
{
	rotate([90, 0, 0])
	union()
	{
		translate([3.5, (-7.5), 0])
			cube([4 + Extra_Mount_Depth, 15, Width]);


		translate([0, (-7.5), 0])
			cube([7.5 + Extra_Mount_Depth, 4, Width]);

		translate([0, 3.5, 0])
			cube([7.5 + Extra_Mount_Depth, 4, Width]);

		difference()
		{
			cylinder(h = Width, d = 15);

			translate([0, 0, (-1)])
				cylinder(h = Width + 2, d = 6);
		}
	}
}

module mount2()
{
	union()
	{

			translate([0, 4, 0])
		flap(3);

		translate([0, 10.5, 0])
		flap(3);
	}
}

module mount3()
{
	union()
	{
		difference()
		{
			translate([0, (-2.5), 0])
				flap(8);

			translate([0, (-8.5), 0])
				nut_hole();
		}

		mount2();
	}
}

module camMount()
{
	translate([(-6.25), (-10.5), 0])
	difference()
	{
		union()
		{
			translate([0, 0, (-3)])
				cylinder(r = 2, h = 3);

			translate([0, 21, (-3)])
				cylinder(r = 2, h = 3);

			translate([(-2), 0, (-3)])
				cube([4, 21, 3]);

			translate([12.5, 0, (-3)])
				cylinder(r = 2, h = 3);

			translate([12.5, 21, (-3)])
				cylinder(r = 2, h = 3);

			translate([10.5, 0, (-3)])
				cube([4, 21, 3]);

			translate([0, (-2), (-3)])
				cube([12.5, 25, 3]);
		}

		translate([0, 0, (-4)])
			cylinder(d = 2.2, h = 5);

		translate([0, 21, (-4)])
			cylinder(d = 2.2, h = 5);

		translate([12.5, 0, (-4)])
			cylinder(d = 2.2, h = 5);

		translate([12.5, 21, (-4)])
			cylinder(d = 2.2, h = 5);
	}
}
union()
{
//* GoPro Mount - 2 flap no nut hole
	translate([0, (-5.75), 10.5])
		rotate([0, 90, 0])
			mount2();
// */

/* GoPro Mount - 3 flap w/nut hole
	translate([0, 0, 10.5])
		rotate([0, 90, 0])
			mount3();
// */

/* GoPro Mount - 2 flap no nut hole
	translate([0, (-5.75), 7.5])
		mount2();
// */

/* GoPro Mount - 3 flap w/nut hole side mount
	translate([0, 0, 7.5])
		mount3();
// */



translate([0, 0, 0])
	*camMount();
  bracket();
  
}

module bracket() {
  difference() {
    translate([-10,-8,-8.75]) cube([20,62,6]);
    translate([0,42,-10]) rotate([0,0,0]) cylinder(r=4,h=10);
  }
}