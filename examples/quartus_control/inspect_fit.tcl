# SPDX-License-Identifier: 0BSD
# Run from one completed project: quartus_cdb -t /path/to/inspect_fit.tcl controlled
package require ::quartus::project
package require ::quartus::chip_planner
if {[llength $quartus(args)] != 1} { error "Supply exactly one project/revision name" }
set project [lindex $quartus(args) 0]
project_open $project -revision $project
read_netlist
get_node_loc
foreach_in_collection node [get_nodes -type lcell] {
    puts "LCELL_NAME [get_node_info -node $node -info name]"
}
project_close
