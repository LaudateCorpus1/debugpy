# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

from __future__ import absolute_import, division, print_function, unicode_literals

from tests import debug
from tests.patterns import some


def test_tracing(pyfile, target, run):
    @pyfile
    def code_to_debug():
        import debuggee
        import debugpy

        debuggee.setup()

        def func(expected_tracing):
            assert debugpy.tracing() == expected_tracing, "inside func({0!r})".format(
                expected_tracing
            )
            print(1)  # @inner1

            # Test nested change/restore. Going from False to True only works entirely
            # correctly on Python 3.6+; on earlier versions, if tracing wasn't enabled
            # when the function is entered, re-enabling it later will not cause the
            # breakpoints in this function to light up. However, it will allow hitting
            # breakpoints in functions called from here.

            def inner2():
                print(2)  # @inner2

            with debugpy.tracing(not expected_tracing):
                assert debugpy.tracing() != expected_tracing, "inside with-statement"
                inner2()
            assert debugpy.tracing() == expected_tracing, "after with-statement"

            print(3)  # @inner3

        assert debugpy.tracing(), "before tracing(False)"
        debugpy.tracing(False)
        assert not debugpy.tracing(), "after tracing(False)"

        print(0)  # @outer1
        func(False)

        debugpy.tracing(True)
        assert debugpy.tracing(), "after tracing(True)"

        print(0)  # @outer2
        func(True)

    with debug.Session() as session:
        with run(session, target(code_to_debug)):
            session.set_breakpoints(code_to_debug, all)

        session.wait_for_stop(expected_frames=[some.dap.frame(code_to_debug, "inner2")])
        session.request_continue()

        session.wait_for_stop(expected_frames=[some.dap.frame(code_to_debug, "outer2")])
        session.request_continue()

        session.wait_for_stop(expected_frames=[some.dap.frame(code_to_debug, "inner1")])
        session.request_continue()

        session.wait_for_stop(expected_frames=[some.dap.frame(code_to_debug, "inner3")])
        session.request_continue()
