// origin.hpp — the signal / background origin of an MCParticle, and the generator particle it descends
// from: one definition for every writer.
//
// The background merger adds a status offset at the generator level, before Geant4 runs, so
// only generator particles carry the band in generatorStatus (1 or 2 signal, >= 1000
// background). Geant4 secondaries have generatorStatus 0 whatever their ancestry; for them
// the first generator ancestor up the parent chain decides.
//
// TimeframeBuilder (EDM4hep mode, after Geant4) adds the offset to every particle of a
// background sub-event, secondaries included: a Geant4 secondary of a SynRad photon carries
// 2000, the photon itself 2001. A status >= 1000 that is a multiple of 1000 is therefore a
// secondary (0 + offset) and gets origin 4 directly; merger files never produce such a status,
// so their prt_origin is unchanged.
//
// prt_origin values written to every CSV:
//   0 unknown, 1 signal, 2 Geant4 secondary of a signal particle,
//   3 background, 4 Geant4 secondary of a background particle.
//
// Trap: the walk follows getParents(0) alone and stops after 200 levels or at a parent that is
// not available (its collection was not read). Changing either changes prt_origin in every CSV;
// the parity gate against the macros catches it.
#pragma once

#include <edm4hep/MCParticleCollection.h>

#include <cstdint>
#include <optional>

/// Band of a generator-level status: 1 signal (status 1 or 2), 3 background (status >= 1000), 0 unknown.
inline int32_t classify_gen_status(int32_t gen_status) {
    if (gen_status == 1 || gen_status == 2) return 1;
    if (gen_status >= 1000) return 3;
    return 0;
}

/// 0 unknown, 1 signal, 2 g4-from-signal, 3 background, 4 g4-from-background.
inline int32_t get_origin_status(const edm4hep::MCParticle& particle) {
    const int32_t gen_status = particle.getGeneratorStatus();
    if (gen_status >= 1000 && gen_status % 1000 == 0) {
        return 4;   // TimeframeBuilder: a Geant4 secondary (status 0) carrying its sub-event's offset
    }
    if (gen_status != 0) {
        return classify_gen_status(gen_status);
    }

    // Geant4 secondary: the first generator ancestor names the band. The depth guard protects
    // against cyclic or broken parent links.
    edm4hep::MCParticle current = particle;
    const int max_depth = 200;
    for (int depth = 0; depth < max_depth; ++depth) {
        if (current.parents_size() == 0) break;
        edm4hep::MCParticle parent = current.getParents(0);
        if (!parent.isAvailable()) break;

        const int32_t parent_status = parent.getGeneratorStatus();
        if (parent_status != 0) {
            const int32_t band = classify_gen_status(parent_status);
            if (band == 1) return 2;
            if (band == 3) return 4;
            return 0;
        }
        current = parent;
    }
    return 0;
}

/// True for a particle the event generator made (a Geant4 primary): any nonzero generatorStatus except a
/// TimeframeBuilder secondary, which carries its sub-event's offset alone (2000, 3000, ...).
inline bool is_generator_particle(const edm4hep::MCParticle& particle) {
    const int32_t gen_status = particle.getGeneratorStatus();
    if (gen_status == 0) return false;
    return !(gen_status >= 1000 && gen_status % 1000 == 0);
}

/// The generator particle a particle descends from, and that particle's daughter on the way down.
/// For a hit of the scattered electron's shower the primary is the electron; for a hit of a Λ decay
/// product (the Λ decays in Geant4) the primary is the Λ and the child is the p, π⁻, n or π⁰.
struct PrimaryAncestry {
    int64_t primary_index = -1;   // index in MCParticles; -1 when the walk finds no generator particle
    int32_t primary_pdg = 0;
    int64_t child_index = -1;     // the primary's daughter on the chain; -1 when the particle is the primary itself
    int32_t child_pdg = 0;
};

/// Walks the getParents(0) chain, the chain get_origin_status walks, with the same 200-level guard;
/// the particle itself counts when it is a generator particle.
inline PrimaryAncestry find_primary_ancestry(const edm4hep::MCParticle& particle) {
    PrimaryAncestry ancestry;
    edm4hep::MCParticle current = particle;
    std::optional<edm4hep::MCParticle> below;   // the particle one step down the chain from `current`
    const int max_depth = 200;
    for (int depth = 0; depth <= max_depth; ++depth) {
        if (is_generator_particle(current)) {
            ancestry.primary_index = current.getObjectID().index;
            ancestry.primary_pdg = current.getPDG();
            if (below) {
                ancestry.child_index = below->getObjectID().index;
                ancestry.child_pdg = below->getPDG();
            }
            return ancestry;
        }
        if (current.parents_size() == 0) break;
        edm4hep::MCParticle parent = current.getParents(0);
        if (!parent.isAvailable()) break;
        below = current;
        current = parent;
    }
    return ancestry;
}
