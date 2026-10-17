"""Adapt the pinned Chromium GN compiler tools without assuming one source layout."""
import re


def add_objc_tools(source):
    path = source / 'build/toolchain/gcc_toolchain.gni'
    text = path.read_text()
    if 'tool("objc")' in text and 'tool("objcxx")' in text:
        return 'already-compatible'
    blocks = []
    for original, name, flags in (('cc', 'objc', 'cflags_objc'), ('cxx', 'objcxx', 'cflags_objcc')):
        # These compiler tools contain no nested scopes. Derive their exact
        # module placeholders/flags from the checked-out Chromium build version.
        matches = list(re.finditer(r'(?m)^    tool\("' + original + r'"\) \{\n.*?^    \}', text, re.DOTALL))
        if len(matches) != 1:
            raise RuntimeError('Inspect the upstream ' + original + ' compiler tool before adding Objective-C')
        block = matches[0][0].replace('tool("' + original + '")', 'tool("' + name + '")', 1)
        block = block.replace('{{cflags_' + ('c' if original == 'cc' else 'cc') + '}}', '{{' + flags + '}}')
        block = block.replace('description = "' + ('CC' if original == 'cc' else 'CXX') + ' ',
                              'description = "' + name.upper() + ' ')
        blocks.append(block)
    marker = '    tool("cxx_module") {'
    if text.count(marker) != 1:
        raise RuntimeError('Ambiguous compiler tool insertion point')
    text = text.replace(marker, '    if (current_os == "mac") {\n' + '\n\n'.join(blocks) + '\n    }\n\n' + marker, 1)
    path.write_text(text)
    return 'added'


def disable_windows_cross_modules(source):
    path = source / 'build/config/BUILDCONFIG.gn'
    text = path.read_text()
    guard = '!(is_win && host_os == "linux")'
    modern = 'use_libcxx_modules = is_clang && ' + guard
    legacy = '_use_libcxx_modules = ' + guard
    guarded = sum(len(re.findall(r'(?m)^\s*' + re.escape(line) + r'\s*$', text))
                  for line in (modern, legacy))
    if guarded != 2:
        for original, replacement in (('use_libcxx_modules = is_clang', modern),
                                      ('_use_libcxx_modules = true', legacy)):
            text, count = re.subn(r'(?m)^([ \t]*)' + re.escape(original) + r'[ \t]*$',
                                  lambda m: m[1] + replacement, text)
            if count == 2:
                break
        else:
            raise RuntimeError('Inspect upstream libc++ module defaults before cross compiling Windows')
    header = 'public_deps += [ "//buildtools/third_party/libc++:headers" ]'
    if header in text:
        def replace(match):
            block = match[0]
            return block.replace('if (is_clang)', 'if (is_clang && ' + guard + ')', 1) if header in block else block
        text = re.sub(r'(?m)^      if \(is_clang\) \{\n(?:^        .*\n)+^      \}', replace, text)
        blocks = re.findall(r'(?m)^      if \(is_clang && ' + re.escape(guard) + r'\) \{\n(?:^        .*\n)+^      \}', text)
        if sum(header in block for block in blocks) != text.count(header):
            raise RuntimeError('Inspect unconditional Chromium libc++ headers dependencies on Windows')
    if path.read_text() == text:
        return 'already-compatible'
    path.write_text(text)
    return 'added'
