from __future__ import annotations

import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import NextTimeStep, ReadOnly, RisingEdge
from cocotb_tools.runner import get_runner

LANGUAGE = os.getenv("HDL_TOPLEVEL_LANG", "verilog").lower().strip()


def compute_winner(freq: list[int]) -> int:
    max_count = max(freq)
    for i, count in enumerate(freq):
        if count == max_count:
            return i
    return 0


@cocotb.test()
async def running_mode_hidden_test(dut):
    """Test running mode with tie-breaking, reset, valid gating, and change_only mode."""

    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start(start_high=False))

    # Initialize inputs
    dut.rst.value = 1
    dut.valid.value = 0
    dut.change_only.value = 0
    dut.data_in.value = 0

    # Python reference model state
    freq = [0] * 128
    winner = 0
    expected_out = 0

    # Apply reset
    await RisingEdge(dut.clk)
    await ReadOnly()

    # After reset, output must be 0
    got = int(dut.mode_out.value)
    assert got == 0, f"After reset expected mode_out=0, got {got}"

    await NextTimeStep()
    dut.rst.value = 0

    def step_reference(valid: int, change_only: int, data_in: int):
        nonlocal freq, winner, expected_out

        if not valid:
            return

        freq[data_in] += 1
        new_winner = compute_winner(freq)

        if change_only:
            if new_winner != winner:
                expected_out = new_winner
            else:
                expected_out = 0
        else:
            expected_out = new_winner

        winner = new_winner

    # Directed sequence:
    # tuple = (valid, change_only, data_in, description)
    sequence = [
        # Normal mode
        (1, 0, 5,  "5 becomes winner -> output 5"),
        (1, 0, 7,  "tie between 5 and 7 -> smaller wins -> output 5"),
        (1, 0, 7,  "7 becomes winner -> output 7"),
        (1, 0, 5,  "tie between 5 and 7 -> smaller wins -> output 5"),
        (0, 0, 9,  "valid low -> ignore input, hold output"),

        # Change-only mode: output winner only when it changes, else 0
        (1, 1, 5,  "winner stays 5 -> output 0"),
        (1, 1, 7,  "winner stays 5 -> output 0"),
        (1, 1, 7,  "7 becomes winner -> output 7"),
        (1, 1, 7,  "winner stays 7 -> output 0"),
        (1, 1, 5,  "winner stays 7 -> output 0"),
        (1, 1, 5,  "tie 5 and 7 -> smaller wins -> winner changes to 5 -> output 5"),

        # More tie-break checks
        (1, 0, 3,  "normal mode, 5 still winner or tie logic applies"),
        (1, 0, 3,  "normal mode, check recomputed winner"),
        (1, 1, 3,  "change-only, only output if winner changes"),
    ]

    for cycle, (valid, change_only, data_in, desc) in enumerate(sequence):
        dut.valid.value = valid
        dut.change_only.value = change_only
        dut.data_in.value = data_in

        # Save old expected output for valid=0 behavior
        old_expected = expected_out

        await RisingEdge(dut.clk)
        await ReadOnly()

        step_reference(valid, change_only, data_in)

        if not valid:
            # Spec says hold output unchanged when valid=0
            expected = old_expected
        else:
            expected = expected_out

        got = int(dut.mode_out.value)
        assert got == expected, (
            f"Cycle {cycle} failed ({desc}): "
            f"valid={valid}, change_only={change_only}, data_in={data_in}, "
            f"expected mode_out={expected}, got {got}"
        )

        await NextTimeStep()

    # Mid-stream reset
    dut.rst.value = 1
    dut.valid.value = 0
    dut.change_only.value = 0
    dut.data_in.value = 0

    await RisingEdge(dut.clk)
    await ReadOnly()

    freq = [0] * 128
    winner = 0
    expected_out = 0

    got = int(dut.mode_out.value)
    assert got == 0, f"After mid-stream reset expected mode_out=0, got {got}"

    await NextTimeStep()
    dut.rst.value = 0

    # Post-reset checks
    post_reset_sequence = [
        (1, 0, 12, "12 becomes winner -> output 12"),
        (1, 1, 3,  "tie 12 and 3 -> smaller wins -> winner changes to 3 -> output 3"),
        (1, 1, 3,  "winner stays 3 -> output 0"),
        (1, 0, 12, "tie 12 and 3 -> smaller wins -> output 3"),
        (1, 0, 12, "12 becomes winner -> output 12"),
        (0, 1, 99, "valid low -> ignore input, hold output"),
    ]

    for cycle, (valid, change_only, data_in, desc) in enumerate(post_reset_sequence):
        dut.valid.value = valid
        dut.change_only.value = change_only
        dut.data_in.value = data_in

        old_expected = expected_out

        await RisingEdge(dut.clk)
        await ReadOnly()

        step_reference(valid, change_only, data_in)

        if not valid:
            expected = old_expected
        else:
            expected = expected_out

        got = int(dut.mode_out.value)
        assert got == expected, (
            f"Post-reset cycle {cycle} failed ({desc}): "
            f"valid={valid}, change_only={change_only}, data_in={data_in}, "
            f"expected mode_out={expected}, got {got}"
        )

        await NextTimeStep()


def test_running_mode_hidden_runner():
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent.parent

    sources = [proj_path / "sources/running_mode.sv"]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="running_mode",
        always=True,
    )

    runner.test(
        hdl_toplevel="running_mode",
        test_module="test_running_mode_hidden",
    )
