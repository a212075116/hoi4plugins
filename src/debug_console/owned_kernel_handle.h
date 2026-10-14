#pragma once
#include <windows.h>
#include <memory>

namespace ClientResource {
struct KernelHandleCloser {
    void operator()(HANDLE handle) const noexcept {
        if (handle && handle != INVALID_HANDLE_VALUE) CloseHandle(handle);
    }
};
using OwnedHandle = std::unique_ptr<void, KernelHandleCloser>;
}
