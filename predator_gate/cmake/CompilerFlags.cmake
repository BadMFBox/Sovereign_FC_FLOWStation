function(apply_compiler_flags target)
    target_compile_options(${target} PRIVATE
        -Wall -Wextra -Wpedantic
        -fstack-protector-strong
        $<$<CONFIG:Release>:-O3>
        $<$<CONFIG:Debug>:-O0 -g>
    )
endfunction()
