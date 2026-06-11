#include "predator_gate.hpp"
#include <iostream>

int main() {
    burner::PredatorGate gate(false);
    
    auto birth = gate.birth_token(1);
    if (!birth.success) {
        std::cerr << "Birth failed\n";
        return 1;
    }
    
    auto admit = gate.admit(1, birth.token_value->data());
    if (!admit.success) {
        std::cerr << "Admit failed\n";
        return 1;
    }
    
    std::cout << "✓ Basic test passed\n";
    return 0;
}
