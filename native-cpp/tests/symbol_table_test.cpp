#include "mcnative/symbol_table.hpp"

#include <cassert>
#include <string>

using namespace mcnative::jvm;

int main() {
    assert(cpp_class_namespace("net/minecraft/client/Main") ==
           "C_net_minecraft_client_Main");
    const auto int_symbol = cpp_method_symbol("load", "()I");
    const auto string_symbol = cpp_method_symbol("load", "()Ljava/lang/String;");
    assert(int_symbol != string_symbol);
    assert(int_symbol.find("M_load_D_") == 0);
    assert(cpp_method_symbol("1<init>", "()V").find("M__1_init__D_") == 0);
    assert(cpp_method_symbol("<init>", "()V") != cpp_method_symbol("_init_", "()V"));

    ClassFile file;
    file.constant_pool.resize(7);
    file.constant_pool[1].tag = 1;
    file.constant_pool[1].text = "sample/Widget";
    file.constant_pool[2].tag = 7;
    file.constant_pool[2].first_index = 1;
    file.constant_pool[3].tag = 1;
    file.constant_pool[3].text = "load";
    file.constant_pool[4].tag = 1;
    file.constant_pool[4].text = "()I";
    file.constant_pool[5].tag = 1;
    file.constant_pool[5].text = "()Ljava/lang/String;";
    file.this_class = 2;

    MemberInfo int_method;
    int_method.name_index = 3;
    int_method.descriptor_index = 4;
    int_method.access_flags = 0x0009;
    MemberInfo string_method;
    string_method.name_index = 3;
    string_method.descriptor_index = 5;
    string_method.access_flags = 0x0009;
    file.methods = {int_method, string_method};

    SymbolTable symbols;
    symbols.add_class(file);
    assert(symbols.class_count() == 1);
    const auto* klass = symbols.find_class("sample/Widget");
    assert(klass != nullptr);
    assert(klass->cpp_namespace == "C_sample_Widget");
    assert(klass->methods.size() == 2);
    assert(symbols.find_method("sample/Widget", "load", "()I") != nullptr);
    assert(symbols.find_method("sample/Widget", "load", "()V") == nullptr);
    assert(symbols.find_method("missing/Widget", "load", "()I") == nullptr);

    bool duplicate_rejected = false;
    try {
        symbols.add_class(file);
    } catch (const SymbolTableError&) {
        duplicate_rejected = true;
    }
    assert(duplicate_rejected);

    file.methods.push_back(int_method);
    SymbolTable duplicate_methods;
    duplicate_rejected = false;
    try {
        duplicate_methods.add_class(file);
    } catch (const SymbolTableError&) {
        duplicate_rejected = true;
    }
    assert(duplicate_rejected);

    ClassFile colliding_class;
    colliding_class.constant_pool.resize(3);
    colliding_class.constant_pool[1].tag = 1;
    colliding_class.constant_pool[1].text = "sample_Widget";
    colliding_class.constant_pool[2].tag = 7;
    colliding_class.constant_pool[2].first_index = 1;
    colliding_class.this_class = 2;
    duplicate_rejected = false;
    try {
        symbols.add_class(colliding_class);
    } catch (const SymbolTableError&) {
        duplicate_rejected = true;
    }
    assert(duplicate_rejected);

    return 0;
}
