// ═══════════════════════════════════════════════════════════════
//  AiZQuad Lab — FC_FLOW MESH Core
//  Common utilities for all rooms
//
//  Founder: Juan Jaime Rivera Zamorano
// ═══════════════════════════════════════════════════════════════

#ifndef AIZQUAD_MESH_CORE_HPP
#define AIZQUAD_MESH_CORE_HPP

#include <string>
#include <memory>
#include <vector>
#include <optional>
#include <functional>

namespace aizquad {
namespace mesh {

// ───────────────────────────────────────────────────────────────
//  Version Info
// ───────────────────────────────────────────────────────────────

struct Version {
    int major;
    int minor;
    int patch;
    
    [[nodiscard]] std::string to_string() const;
    [[nodiscard]] bool is_compatible_with(const Version& other) const;
};

constexpr Version MESH_VERSION{1, 0, 0};

// ───────────────────────────────────────────────────────────────
//  Room Interface
// ───────────────────────────────────────────────────────────────

class IRoom {
public:
    virtual ~IRoom() = default;
    
    [[nodiscard]] virtual std::string name() const = 0;
    [[nodiscard]] virtual Version version() const = 0;
    [[nodiscard]] virtual bool is_initialized() const = 0;
    
    virtual bool initialize() = 0;
    virtual void shutdown() = 0;
};

// ───────────────────────────────────────────────────────────────
//  Surface (AI Interface)
// ───────────────────────────────────────────────────────────────

template<typename T>
class Surface {
public:
    explicit Surface(std::shared_ptr<T> impl) 
        : impl_(std::move(impl)) {}
    
    [[nodiscard]] T* operator->() const { return impl_.get(); }
    [[nodiscard]] T& operator*() const { return *impl_; }
    [[nodiscard]] bool is_valid() const { return impl_ != nullptr; }
    
private:
    std::shared_ptr<T> impl_;
};

// ───────────────────────────────────────────────────────────────
//  Lock Verification
// ───────────────────────────────────────────────────────────────

class LogicLock {
public:
    struct Signature {
        std::string hash;
        std::string algorithm;
        uint64_t timestamp;
    };
    
    [[nodiscard]] static std::optional<Signature> 
    verify(const std::string& room_name);
    
    [[nodiscard]] static bool 
    is_tampered(const std::string& room_name);
};

// ───────────────────────────────────────────────────────────────
//  Dependency Graph
// ───────────────────────────────────────────────────────────────

class DependencyGraph {
public:
    using RoomName = std::string;
    using DependencyList = std::vector<RoomName>;
    
    void add_room(const RoomName& room, const DependencyList& deps);
    
    [[nodiscard]] std::optional<std::vector<RoomName>> 
    topological_sort() const;
    
    [[nodiscard]] std::vector<std::vector<RoomName>> 
    detect_cycles() const;
    
    [[nodiscard]] bool has_cycles() const;
    
private:
    std::unordered_map<RoomName, DependencyList> graph_;
};

// ───────────────────────────────────────────────────────────────
//  Error Handling
// ───────────────────────────────────────────────────────────────

class MeshError : public std::runtime_error {
public:
    explicit MeshError(const std::string& msg) 
        : std::runtime_error(msg) {}
};

class RoomNotFoundError : public MeshError {
public:
    explicit RoomNotFoundError(const std::string& room) 
        : MeshError("Room not found: " + room) {}
};

class SignatureError : public MeshError {
public:
    explicit SignatureError(const std::string& msg) 
        : MeshError("Signature verification failed: " + msg) {}
};

class CyclicDependencyError : public MeshError {
public:
    explicit CyclicDependencyError(const std::string& cycle) 
        : MeshError("Cyclic dependency detected: " + cycle) {}
};

} // namespace mesh
} // namespace aizquad

#endif // AIZQUAD_MESH_CORE_HPP
