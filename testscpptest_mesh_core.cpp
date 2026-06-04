# ═══════════════════════════════════════════════════════════════
#  tests/cpp/test_mesh_core.cpp
#  C++ Core Tests — GoogleTest
# ═══════════════════════════════════════════════════════════════

#include <gtest/gtest.h>
#include <string>
#include <vector>
#include <optional>
#include <unordered_map>
#include <unordered_set>
#include <stdexcept>

// ───────────────────────────────────────────────────────────────
//  Inline implementations to test in isolation
//  (mirrors aizquad/mesh_core.hpp logic)
// ───────────────────────────────────────────────────────────────

namespace aizquad {
namespace mesh {

struct Version {
    int major, minor, patch;

    std::string to_string() const {
        return std::to_string(major) + "."
             + std::to_string(minor) + "."
             + std::to_string(patch);
    }

    bool is_compatible_with(const Version& other) const {
        return major == other.major;
    }
};

// ── Dependency Graph ──────────────────────────────────────────

class DependencyGraph {
public:
    using RoomName       = std::string;
    using DependencyList = std::vector<RoomName>;

    void add_room(const RoomName& room, const DependencyList& deps) {
        graph_[room] = deps;
    }

    bool has_cycles() const {
        std::unordered_set<RoomName> visited;
        std::unordered_set<RoomName> rec_stack;

        for (const auto& [node, _] : graph_) {
            if (visited.find(node) == visited.end()) {
                if (dfs(node, visited, rec_stack)) return true;
            }
        }
        return false;
    }

    std::optional<std::vector<RoomName>> topological_sort() const {
        if (has_cycles()) return std::nullopt;

        std::unordered_map<RoomName, int> in_degree;
        for (const auto& [node, _] : graph_) in_degree[node] = 0;

        for (const auto& [node, deps] : graph_) {
            for (const auto& dep : deps) {
                if (in_degree.count(dep)) in_degree[dep]++;
            }
        }

        std::vector<RoomName> queue, result;
        for (const auto& [node, deg] : in_degree) {
            if (deg == 0) queue.push_back(node);
        }

        while (!queue.empty()) {
            RoomName node = queue.back();
            queue.pop_back();
            result.push_back(node);
            for (const auto& dep : graph_.at(node)) {
                if (--in_degree[dep] == 0) queue.push_back(dep);
            }
        }
        return result;
    }

private:
    std::unordered_map<RoomName, DependencyList> graph_;

    bool dfs(
        const RoomName& node,
        std::unordered_set<RoomName>& visited,
        std::unordered_set<RoomName>& rec_stack
    ) const {
        visited.insert(node);
        rec_stack.insert(node);

        if (graph_.count(node)) {
            for (const auto& dep : graph_.at(node)) {
                if (!visited.count(dep) && dfs(dep, visited, rec_stack))
                    return true;
                if (rec_stack.count(dep))
                    return true;
            }
        }
        rec_stack.erase(node);
        return false;
    }
};

} // namespace mesh
} // namespace aizquad

using namespace aizquad::mesh;

// ───────────────────────────────────────────────────────────────
//  VERSION TESTS
// ───────────────────────────────────────────────────────────────

TEST(VersionTest, ToStringFormatsCorrectly) {
    Version v{1, 2, 3};
    EXPECT_EQ(v.to_string(), "1.2.3");
}

TEST(VersionTest, ZeroPatchFormatsCorrectly) {
    Version v{2, 0, 0};
    EXPECT_EQ(v.to_string(), "2.0.0");
}

TEST(VersionTest, SameMajorIsCompatible) {
    Version v1{1, 0, 0};
    Version v2{1, 5, 3};
    EXPECT_TRUE(v1.is_compatible_with(v2));
}

TEST(VersionTest, DifferentMajorIsIncompatible) {
    Version v1{1, 0, 0};
    Version v2{2, 0, 0};
    EXPECT_FALSE(v1.is_compatible_with(v2));
}

TEST(VersionTest, CompatibilityIsSymmetric) {
    Version v1{1, 0, 0};
    Version v2{1, 9, 9};
    EXPECT_EQ(
        v1.is_compatible_with(v2),
        v2.is_compatible_with(v1)
    );
}

// ───────────────────────────────────────────────────────────────
//  DEPENDENCY GRAPH TESTS
// ───────────────────────────────────────────────────────────────

class DependencyGraphTest : public ::testing::Test {
protected:
    DependencyGraph graph;
};

TEST_F(DependencyGraphTest, EmptyGraphHasNoCycles) {
    EXPECT_FALSE(graph.has_cycles());
}

TEST_F(DependencyGraphTest, SingleNodeHasNoCycles) {
    graph.add_room("a", {});
    EXPECT_FALSE(graph.has_cycles());
}

TEST_F(DependencyGraphTest, LinearChainHasNoCycles) {
    graph.add_room("a", {});
    graph.add_room("b", {"a"});
    graph.add_room("c", {"b"});
    EXPECT_FALSE(graph.has_cycles());
}

TEST_F(DependencyGraphTest, DirectCycleDetected) {
    graph.add_room("a", {"b"});
    graph.add_room("b", {"a"});
    EXPECT_TRUE(graph.has_cycles());
}

TEST_F(DependencyGraphTest, IndirectCycleDetected) {
    graph.add_room("a", {"b"});
    graph.add_room("b", {"c"});
    graph.add_room("c", {"a"});
    EXPECT_TRUE(graph.has_cycles());
}

TEST_F(DependencyGraphTest, DiamondGraphHasNoCycles) {
    graph.add_room("a", {});
    graph.add_room("b", {"a"});
    graph.add_room("c", {"a"});
    graph.add_room("d", {"b", "c"});
    EXPECT_FALSE(graph.has_cycles());
}

TEST_F(DependencyGraphTest, TopologicalSortReturnsNulloptOnCycle) {
    graph.add_room("a", {"b"});
    graph.add_room("b", {"a"});
    auto result = graph.topological_sort();
    EXPECT_FALSE(result.has_value());
}

TEST_F(DependencyGraphTest, TopologicalSortLinearOrder) {
    graph.add_room("a", {});
    graph.add_room("b", {"a"});
    graph.add_room("c", {"b"});

    auto result = graph.topological_sort();
    ASSERT_TRUE(result.has_value());

    auto& order = result.value();
    auto pos = [&](const std::string& n) {
        return std::find(order.begin(), order.end(), n) - order.begin();
    };

    EXPECT_LT(pos("a"), pos("b"));
    EXPECT_LT(pos("b"), pos("c"));
}

TEST_F(DependencyGraphTest, TopologicalSortDiamond) {
    graph.add_room("a", {});
    graph.add_room("b", {"a"});
    graph.add_room("c", {"a"});
    graph.add_room("d", {"b", "c"});

    auto result = graph.topological_sort();
    ASSERT_TRUE(result.has_value());

    auto& order = result.value();
    auto pos = [&](const std::string& n) {
        return std::find(order.begin(), order.end(), n) - order.begin();
    };

    EXPECT_LT(pos("a"), pos("b"));
    EXPECT_LT(pos("a"), pos("c"));
    EXPECT_LT(pos("b"), pos("d"));
    EXPECT_LT(pos("c"), pos("d"));
}

TEST_F(DependencyGraphTest, TopologicalSortContainsAllNodes) {
    graph.add_room("a", {});
    graph.add_room("b", {"a"});
    graph.add_room("c", {"a"});

    auto result = graph.topological_sort();
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result.value().size(), 3u);
}

// ───────────────────────────────────────────────────────────────
//  ENTRY POINT
// ───────────────────────────────────────────────────────────────

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
