### unit test the buffer handler

from terminal.buffer_handler import BufferHandler

### Deprecated! 
### This file is going out of use as the project's direction 
### is making a minor change and tokens can be read from 
### claude's jsonl files

'''
def test_enter():
    bh = BufferHandler()
    bh.buffer = 'test'
    bh.handle_enter()
    assert bh.buffer == ''

def test_backspace():
    bh = BufferHandler()
    bh.buffer = 'test'
    bh.handle_backspace()
    assert bh.buffer=='tes'

def test_backspace_empty_buffer():
    bh = BufferHandler()
    bh.buffer = ''
    bh.handle_backspace()
    assert bh.buffer == ''

def test_clean_usr_input():
    bh = BufferHandler()
    bh.clean_usr_input('a'.encode('utf-8'))
    assert bh.buffer == 'a'
    bh.clean_usr_input('bc'.encode('utf-8'))
    assert bh.buffer == 'abc'

def test_clean_usr_input_backspace():
    bh = BufferHandler()
    bh.buffer = 'test'
    bh.clean_usr_input('\b'.encode('utf-8'))
    assert bh.buffer == 'tes'

def test_clean_usr_input_enter():
    bh = BufferHandler()
    bh.buffer = 'test'
    bh.clean_usr_input('\r'.encode('utf-8'))
    assert bh.buffer == ''

def test_clean_usr_input_focus():
    bh = BufferHandler()
    bh.clean_usr_input('\x1b[I'.encode('utf-8'))
    assert bh.buffer == ''
    bh.clean_usr_input('\x1b[O'.encode('utf-8'))
    assert bh.buffer == ''

def test_get_clean_buffer():
    bh = BufferHandler()
    usr_input = 'test'.encode('utf-8')
    ret = bh.get_clean_buffer(usr_input)
    assert ret == usr_input
'''