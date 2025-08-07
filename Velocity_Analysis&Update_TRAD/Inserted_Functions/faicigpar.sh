# -----------------------------------------------------------------------------
# Function: faicigpar - Replaces the Fortran program of the same name
# 
# Purpose: Processes pick data to generate CIG parameters
# Inputs: 
#   - nciclo.txt: Contains pick index and CDP number
#   - mpicks.txt: Contains depth and r-value picks
# Outputs:
#   - cig.txt: Formatted CIG parameters
# -----------------------------------------------------------------------------

faicigpar() {
    # Verify required input files exist
    if [[ ! -f "nciclo.txt" || ! -f "mpicks.txt" ]]; then
        echo "ERROR: [faicigpar] Required files (nciclo.txt, mpicks.txt) not found"
        exit 1
    fi
    
    # Read values from input files
    local nc=$(head -1 nciclo.txt)        # Pick index
    local ncdp=$(tail -1 nciclo.txt)      # CDP number
    
    # Validate pick index
    local total_picks=$(wc -l < mpicks.txt)
    if [[ $nc -le 0 || $nc -gt $total_picks ]]; then
        echo "ERROR: [faicigpar] Invalid pick index: $nc (valid range: 1-$total_picks)"
        exit 1
    fi
    
    # Read depth and r-value from the specified pick
    read -r z r < <(sed -n "${nc}p" mpicks.txt)
    
    # Format output parameters (preserving decimal precision)
    printf "cip=%d,%.4f,%.8f\n" "$ncdp" "$z" "$r" > cig.txt
    
    echo "Generated cig.txt for CDP $ncdp, pick $nc"
}
