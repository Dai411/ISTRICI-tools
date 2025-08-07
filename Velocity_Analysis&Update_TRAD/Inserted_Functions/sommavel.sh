sommavel() {
    log info "Adding velocity models..."
    local required_files=("velres.dat" "vfile.a" "v.par_v")
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log error "Missing required file: $file"
            return 1
        fi
    done
    local params=()
    while IFS= read -r line; do
        for val in $line; do
            params+=($val)
        done
    done < "v.par_v"
    if [ ${#params[@]} -lt 9 ]; then
        log error "v.par_v must contain at least 9 values (found ${#params[@]})"
        return 1
    fi
    local nz=${params[0]} dz=${params[1]} fz=${params[2]}
    local nx=${params[3]} dx=${params[4]} fx=${params[5]}
    local ncdpmin=${params[6]} cdpmax=${params[7]} dcdp=${params[8]}
    validate_number "$nz" "nz" || return 1
    validate_float "$dz" "dz" || return 1
    validate_float "$fz" "fz" || return 1
    validate_number "$nx" "nx" || return 1
    validate_float "$dx" "dx" || return 1
    validate_float "$fx" "fx" || return 1
    local total_points=$((nx * nz))
    log info "Grid dimensions: ${nx}x${nz} = $total_points points"
    local velres_lines=$(wc -l < "velres.dat")
    local vfile_lines=$(wc -l < "vfile.a")
    if [ "$velres_lines" -ne "$total_points" ]; then
        log error "velres.dat size mismatch (expected: $total_points, actual: $velres_lines)"
        return 1
    fi
    if [ "$vfile_lines" -ne "$total_points" ]; then
        log error "vfile.a size mismatch (expected: $total_points, actual: $vfile_lines)"
        return 1
    fi
    local start_time=$(date +%s.%N)
    paste "vfile.a" "velres.dat" | awk -v total="$total_points" '
    BEGIN {
        count = 0
        step = (total > 100) ? int(total/100) : 1
        print "0% completed" > "/dev/stderr"
    }
    {
        count++
        if (step > 0 && count % step == 0) {
            progress = int(count/total*100)
            printf "\rProcessing: %d%% completed", progress > "/dev/stderr"
            system("") # Flush output buffer
        }
        printf "%.8f\n", $1 + $2
    }
    END {
        if (total > 0) printf "\rProcessing: 100%% completed\n" > "/dev/stderr"
    }' > "vfile.updated"
    local end_time=$(date +%s.%N)
    local elapsed=$(echo "$end_time - $start_time" | bc -l)
    local points_per_sec=$(echo "scale=2; $total_points / $elapsed" | bc)
    log info "Addition completed in ${elapsed}s (${points_per_sec} points/sec)"
    log info "Created updated velocity model: vfile.updated"
    return 0
}
