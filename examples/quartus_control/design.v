// SPDX-License-Identifier: 0BSD
// One observed combinational boundary, two equivalent registers, one unused register.
module control_demo(input clk, input a, input b, output q0, output q1);
`ifdef MAXVELL_KEEP_STRUCTURE
    (* keep = 1 *) wire probe_comb;
    (* preserve, dont_merge *) reg r0, r1;
    (* preserve, noprune *) reg orphan;
`else
    wire probe_comb;
    reg r0, r1;
    reg orphan;
`endif
    assign probe_comb = a ^ b;
    always @(posedge clk) begin
        r0 <= probe_comb;
        r1 <= probe_comb;
        orphan <= a;
    end
    assign q0 = r0;
    assign q1 = r1;
endmodule
