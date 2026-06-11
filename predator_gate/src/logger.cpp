#include "logger.hpp"

namespace burner {

RLog& get_logger() noexcept {
    return RLog::instance();
}

} // namespace burner
