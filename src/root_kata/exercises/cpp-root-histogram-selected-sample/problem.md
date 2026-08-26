# Turn a selection into a distribution

An analysis often asks two different questions:

1. which values survive the physics selection?
2. where do the surviving values land in the histogram?

Implement a strict `value > threshold` selection and fill only survivors into a 5-bin histogram covering `[0,150]`.

## Predict before coding

For `20, 50, 50.1, 80, 120` with threshold `50`, how many values survive?

Then consider `10` and `151` with threshold `0`: both survive the selection, but are both visible in the histogram?

The tests keep those two decisions separate.
