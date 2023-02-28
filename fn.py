#!/usr/bin/env python3

import regex
import sys
import os
import datetime


def skip_file(fname):
    import cq
    global ns
    if ns:
        return False

    for skip in cq.SKIP_DIRS:
        if skip.search(fname):
            return True
    for skip in cq.SKIP_EXTS:
        if skip.search(fname):
            return True
    return False


def get_global_checks(re_checks_todo):
    import cq  # noqa
    global_checks = []
    for c in cq.GLOBAL_CHECKS:
        check_name = c[0]
        proc = c[1]
        arg = c[2]
        if re_checks_todo.search(check_name):
            global_checks += [(check_name, proc, arg)]
    return global_checks


def get_global_post_checks(re_checks_todo):
    import cq  # noqa
    global_checks = []
    for c in cq.GLOBAL_POST_CHECKS:
        check_name = c[0]
        proc = c[1]
        arg = c[2]
        if re_checks_todo.search(check_name):
            global_checks += [(check_name, proc, arg)]
    return global_checks


def get_file_checks(fname, re_checks_todo):
    import cq
    # FILENAME_CHECKS, 0 is regex, 1 is outfile
    file_checks = []
    for c in cq.FILE_CHECKS:
        check_name = c[0]
        regex_text = c[1]
        proc = c[2]
        arg = c[3]
        if regex_text.search(fname):
            if re_checks_todo.search(check_name):
                file_checks += [(check_name, regex_text, proc, arg)]
    return file_checks


def get_line_regex_checks(fname, re_checks_todo):
    import cq
    global sc, sa  # noqa

    # compile regexes
    line_checks = []
    for c in cq.LINE_REGEX_CHECKS:
        check_name = c[0]
        check_re = c[1]
        files = c[2] if len(c) > 2 else None
        exclusions = c[3] if len(c) > 3 else None
        fmt = c[4] if len(c) > 4 else None

        add = True
        if sc:
            files = cq.ALL_CODE_FILES

        if sa:
            add = True
        elif files:
            add = False
            for f in files:
                if fname.lower().endswith(f):
                    add = True
                    break

        if add:
            if re_checks_todo.search(check_name):
                line_checks += [(check_name, check_re, files, exclusions, fmt)]
    for ext in cq.C_FILES:
        if fname.lower().endswith(ext):
            for fn in cq.BannedFunctions:
                re = regex.compile(re_checks_todo)
                if re.search('banned_' + fn):
                    line_checks += [('banned_' + fn, regex.compile(r'\W' + fn + r'\s*\(.{0,99}$'), None, None)]

    return line_checks


def get_line_custom_checks(fname, re_checks_todo):
    import cq
    global sc, sa  # noqa

    # compile regexes
    line_checks = []
    for c in cq.LINE_CUSTOM_CHECKS:
        check_name = c[0]
        check_fn = c[1]
        files = c[2] if len(c) > 2 else None
        exclusions = c[3] if len(c) > 3 else None
        fmt = c[4] if len(c) > 4 else None

        add = True
        if sc:
            files = cq.ALL_CODE_FILES

        if sa:
            add = True
        elif files:
            add = False
            for f in files:
                if fname.lower().endswith(f):
                    add = True
                    break
        if add:
            if re_checks_todo.search(check_name):
                line_checks += [(check_name, check_fn, files, exclusions, fmt)]

    return line_checks


def do_file_check(check, fname):
    out_fname = outdir + '/' + check[0] + '.txt'
    # regex_text = check[1]
    proc = check[2]
    arg = check[3]
    proc(fname, out_fname, arg)


def do_line_regex_check(check, fname, line, line_num):
    try:
        outfile = check[0]
        re = check[1]
        # files = check[2] if len(check) > 2 else None
        exclusions = check[3] if len(check) > 3 else None
        fmt = check[4] if len(check) > 4 else '{fname}:{line_num}:{g0}'
        if fmt is None: fmt = '{fname}:{line_num}:{g0}'  # noqa
        result = re.search(line)
        if result:
            skip = False
            if exclusions:
                for exclude in exclusions:
                    res_ex = exclude.search(line)
                    if res_ex:
                        skip = True
                        break
            if not skip:
                # write output in format.
                # string.format?
                g0 = result.group(0)
                groups = result.groups()
                g1 = groups[0] if len(groups) > 0 else ''
                g2 = groups[1] if len(groups) > 1 else ''
                g3 = groups[2] if len(groups) > 2 else ''

                msg = fmt.format(fname=fname, line_num=line_num, g0=g0, g1=g1, g2=g2, g3=g3)
                write_result(outfile, msg)
    except Exception as e:
        print("Exception: " + str(e))
        print("")


def do_line_custom_check(check, fname, line, line_num):
    try:
        outfile = check[0]
        fn = check[1]
        base_fmt = '{fname}:{line_num}:{g0}'
        # files = check[2] if len(check) > 2 else None
        # exclusions = check[3] if len(check) > 3 else None
        fmt = check[4] if len(check) > 4 else base_fmt
        if fmt is None: fmt = base_fmt  # noqa
        results = fn(line)
        for result, score in results:  # noqa
            score_str = '%02d' % score
            g0 = result
            msg = fmt.format(fname=fname, line_num=line_num, score_str=score_str, g0=g0)
            write_result('crit_' + outfile, msg)  # noqa

    except Exception as e:
        print("Exception: " + str(e))
        print("")


def global_run_tool(out_fname, arg):
    cmd = arg.format(out_fname=out_fname)
    os.system(cmd)


def do_global_check(check):
    check_name = check[0]
    out_fname = outdir + '/' + check_name + '.txt'
    proc = check[1]
    arg = check[2]
    if print_progress:
        print('Running Tool: ' + check_name)
    proc(out_fname, arg)


def sort_file(filename):
    try:
        in_file = open(filename, 'r')
        lines = sorted(set(in_file.readlines()))
        in_file.close()
        in_file = open(filename, 'w')
        in_file.writelines(lines)
        in_file.close()
    except:  # noqa
        return False


def sort_df_sources_and_sinks(out_fname, arg):  # noqa
    import cq
    for source_file in cq.DF_FILES:
        source_file = outdir + '/' + source_file + '_sources.txt'
        sort_file(source_file)
        source_file = outdir + '/' + source_file + '_sinks.txt'
        sort_file(source_file)


def df_report_if_issue(df_file, src_result, sink_result):
    # True if strings match to the first colon ':'
    lhs = src_result.split(':')
    rhs = sink_result.split(':')
    if len(lhs) < 2 or len(rhs) < 2:
        return False
    if lhs[0] != rhs[0]:
        return False
    i_l = int(lhs[1])
    i_r = int(rhs[1])
    diff = abs(i_l - i_r)
    if diff > 1000:
        return False
    msg = lhs[0] + ':' + lhs[1] + ':SCORE:' + f'{diff:05}'
    write_result(df_file + '_issues.txt', msg)
    return True


def gen_df_bugs(out_fname, arg):  # noqa
    import cq  # noqa
    for df_file in cq.DF_FILES:
        source_file = outdir + '/' + df_file + '_sources.txt'
        sink_file = outdir + '/' + df_file + '_sinks.txt'

        # for each source, advance sink to 'first after'; numeric (not alpha) comparison for line number.
        # compare two lines. Same file is line_number diff.
        # Output issues with prefix of 'score', which is this diff.
        try:
            in_file = open(source_file, 'r')
            src_lines = in_file.readlines()
            in_file.close()
            in_file = open(sink_file, 'r')
            sink_lines = in_file.readlines()
            in_file.close()
        except:  # noqa
            continue

        i_src = 0
        i_sink = 0
        while (i_src < len(src_lines)) and (i_sink < len(sink_lines)):
            src = src_lines[i_src]
            sink = sink_lines[i_sink]
            while (sink < src) and (i_sink < len(sink_lines)):
                sink = sink_lines[i_sink]
                i_sink = i_sink + 1
            df_report_if_issue(df_file, src, sink)
            i_src = i_src + 1


def basic_get_time(out_fname, arg):
    now = datetime.datetime.now()
    start = now.strftime("%Y-%m-%d %H:%M:%S")
    write_result_to_path(out_fname, start + arg)


def basic_path(out_fname, arg):
    write_result_to_path(out_fname, os.path.abspath(".") + arg)


def file_run_tool(fname, out_fname, arg):
    cmd = arg.format(fname=fname, out_fname=out_fname)
    os.system(cmd)


def file_scan_exe(fname, out_fname, arg):  # noqa
    write_result_to_path(out_fname, fname)


def file_exists(fname, out_fname, arg):  # noqa
    write_result_to_path(out_fname, fname)


def file_scan_shell(fname, out_fname, arg):  # noqa
    write_result_to_path(out_fname, 'Scan shell: ' + fname)
    cmdline = 'shellcheck "{fname}" >> "{out_fname}"'
    cmd = cmdline.format(fname=fname, out_fname=out_fname)
    os.system(cmd)


def write_result(fname, result_msg):
    with open(outdir + '/' + fname + '.txt', 'a') as outfile:
        if result_msg.endswith('\n'):
            outfile.write(result_msg)
        else:
            outfile.write(result_msg + '\n')


def write_result_to_path(fullpath, result_msg):
    with open(fullpath, 'a') as outfile:
        if result_msg.endswith('\n'):
            outfile.write(result_msg)
        else:
            outfile.write(result_msg + '\n')


def is_binary(line):
    if line.find(b'\x00'):
        return True
    if line.find(b'\xff'):
        return True
    if line.find(b'\xfe'):
        return True
    return False


def do_checks(re_checks_todo):
    if outdir == '':
        return
    if a:
        mode = 'rb'
    else:
        mode = 'r'

    global_checks = get_global_checks(re_checks_todo)
    for check in global_checks:
        do_global_check(check)

    for root, subdirs, files in os.walk(os.path.abspath(".")):
        for fn in files:
            fname = str(root) + "/" + str(fn)
            # exclude some files/paths based on verbosity options
            if skip_file(fname):
                continue
            if vvv or print_progress:
                print('Scanning ' + fname)
            # do checks based on filename
            file_checks = get_file_checks(fname, re_checks_todo)
            for check in file_checks:
                do_file_check(check, fname)

            # do checks based on the text of lines in a file
            regex_checks = get_line_regex_checks(fname, re_checks_todo)
            custom_checks = get_line_custom_checks(fname, re_checks_todo)
            if regex_checks or custom_checks:
                try:
                    with open(fname, mode) as f:
                        line_num = 1
                        for line in f:
                            # do all line checks
                            if a:
                                line = str(line)
                            for check in regex_checks:
                                do_line_regex_check(check, fname, line, line_num)
                            for check in custom_checks:
                                do_line_custom_check(check, fname, line, line_num)

                            line_num += 1
                except:  # noqa
                    continue

    checks = get_global_post_checks(re_checks_todo)
    for check in checks:
        do_global_check(check)


def syntax():
    print(
        '''cq.py : Universal SAST Tool [ By Chris Anley ]
        Syntax: 
        cq.py [options] <output directory>
        -a   : check all files, including binaries (i.e. files containing invalid utf-8 chars)
        -c <checks regex> : only run checks matching the regex, e.g. 'php'
        -p   : print progress
        -v   : quite verbose
        -vv  : annoyingly verbose
        -vvv : pointlessly verbose
        -ns  : no skip : don't skip files/directories that are irrelevant, like test, /vendor/, /node_modules/, .zip etc
        -sa  : scan all files, not just recommended / code files
        -sc  : scan all code files for all bugs, i.e. not just python bugs in python files
        ''')


a = False
v = False
vv = False
vvv = False
ns = False
sa = False
sc = False
print_progress = False
re_checks = '.*'
outdir = '/tmp/'  # Note - this is always set to something else, but - just in case it isn't, put output in /tmp.


def do_main():
    global a, v, vv, vvv, ns, sa, sc, outdir, print_progress, re_checks
    argc = len(sys.argv)
    argv = sys.argv

    if argc <= 1:
        return syntax()

    for i in range(1, argc):
        if argv[i] == '-a':
            a = True
            ns = True  # no skip directories
            sa = True  # apply all checks to all files
            continue
        if argv[i] == '-v':
            v = True
            continue
        if argv[i] == '-vv':
            v = True
            vv = True
            continue
        if argv[i] == '-vvv':
            v = True
            vv = True
            vvv = True
            continue
        if argv[i] == '-ns':  # no skip directories / files
            ns = True
            continue
        if argv[i] == '-sa':  # apply all checks to all files
            sa = True
            continue
        if argv[i] == '-sc':  # apply all checks to all code files
            sc = True
            continue
        if argv[i] == '-p':
            print_progress = True
        if i == argc - 1:
            outdir = argv[i]
        if argv[i] == '-c':
            re_checks = argv[i + 1]
            i += 1

    try:
        os.makedirs(outdir)
    except:  # noqa
        print("Outdir exists")

    print("Starting")

    do_checks(regex.compile(re_checks))
